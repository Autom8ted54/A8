"""Tests voor scraper.e_procurement — parsing en paginering, zonder netwerk."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from database.models import RawTender
from mailer.run import drop_ted_duplicates
from scraper.e_procurement import EProcurementSource, _pick_lang, ted_number_key


def _nl(text: str) -> list[dict]:
    return [{"language": "FR", "text": f"FR {text}"}, {"language": "NL", "text": text}]


SAMPLE_PUB = {
    "referenceNumber": "11e59b62_002",
    "noticeSubType": "16",
    "cpvMainCode": {"code": "79340000-9", "descriptions": _nl("Reclame- en marketingdiensten")},
    "cpvAdditionalCodes": [{"code": "79341000-6"}, {"code": "79340000-9"}],
    "dossier": {"titles": _nl("Communicatiecampagne"), "descriptions": _nl("Beschrijving")},
    "organisation": {"organisationNames": _nl("Stad Gent")},
    "vaultSubmissionDeadline": "2026-12-01T10:00:00",
    "publicationWorkspaceId": "ws-1",
    "publicationReferenceNumbersTED": [],
}


def _source(session: MagicMock | None = None) -> EProcurementSource:
    return EProcurementSource(
        "id", "secret", "https://public.int.fedservices.be/api/oauth2/token", session=session or MagicMock()
    )


def test_pick_lang_prefers_dutch():
    assert _pick_lang(_nl("NL-tekst")) == "NL-tekst"


def test_pick_lang_falls_back_to_first_available():
    assert _pick_lang([{"language": "DE", "text": "DE"}]) == "DE"
    assert _pick_lang(None) is None
    assert _pick_lang([]) is None


def test_api_base_derived_from_token_url():
    assert _source().api_base == "https://public.int.fedservices.be/api"


def test_to_raw_tender_maps_fields():
    t = _source()._to_raw_tender(SAMPLE_PUB)
    assert t.source == "e-procurement"
    assert t.source_ref == "11e59b62_002"
    assert t.title == "Communicatiecampagne"
    assert t.authority == "Stad Gent"
    assert t.cpv_codes == ["79340000", "79341000"]  # zonder controlecijfer, gededupliceerd
    assert t.deadline == date(2026, 12, 1)
    assert t.url == "https://www.publicprocurement.be/publication-workspaces/ws-1/general"
    assert t.country == "BE"


def test_to_raw_tender_handles_minimal_publication():
    t = _source()._to_raw_tender({"referenceNumber": "X"})
    assert t.title == "(geen titel)"
    assert t.authority is None
    assert t.deadline is None
    assert t.url is None
    assert t.cpv_codes == []


@pytest.mark.parametrize(
    ("ref", "key"),
    [
        ("00123456-2026", "123456-2026"),
        ("123456-2026", "123456-2026"),
        ("2026/S 210-123456", "123456-2026"),
        ("11e59b62-1da4-456f_001", None),
    ],
)
def test_ted_number_key(ref, key):
    assert ted_number_key(ref) == key


def _mock_response(payload: dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_fetch_recent_filters_on_subtype_and_cpv_and_paginates():
    session = MagicMock()
    session.post.return_value = _mock_response({"access_token": "tok", "expires_in": 3600})
    award = {**SAMPLE_PUB, "noticeSubType": "29"}
    medical = {**SAMPLE_PUB, "cpvMainCode": {"code": "33000000-0"}, "cpvAdditionalCodes": []}
    page1 = {"publications": [SAMPLE_PUB] * 98 + [award, medical], "totalCount": 150}
    page2 = {"publications": [SAMPLE_PUB] * 50, "totalCount": 150}
    session.get.side_effect = [_mock_response(page1), _mock_response(page2)]

    tenders = _source(session).fetch_recent()
    assert len(tenders) == 148
    assert session.get.call_count == 2
    assert session.post.call_count == 1  # token hergebruikt
    headers = session.get.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer tok"
    assert headers["BelGov-Trace-Id"]
    assert session.get.call_args.kwargs["params"]["page"] == 2


def test_token_failure_does_not_leak_body():
    session = MagicMock()
    session.post.return_value = _mock_response({"error": "invalid_client id"}, status=401)
    with pytest.raises(RuntimeError) as exc:
        _source(session).fetch_recent()
    assert "HTTP 401" in str(exc.value)
    assert "invalid_client" not in str(exc.value)


def test_from_env_none_when_not_configured(monkeypatch):
    monkeypatch.delenv("EPROC_ENV", raising=False)
    assert EProcurementSource.from_env() is None


def test_from_env_raises_on_missing_vars(monkeypatch):
    monkeypatch.setenv("EPROC_ENV", "pr")
    for k in ("CLIENT_ID", "CLIENT_SECRET", "TOKEN_URL"):
        monkeypatch.delenv(f"EPROC_PR_{k}", raising=False)
    with pytest.raises(RuntimeError, match="EPROC_PR_CLIENT_ID"):
        EProcurementSource.from_env()


def test_drop_ted_duplicates_keeps_unknown_notices():
    eproc = [RawTender(source="e-procurement", source_ref="a", title="x", raw={"publicationReferenceNumbersTED": ["123456-2026"]})]
    ted = [
        RawTender(source="ted", source_ref="00123456-2026", title="dubbel"),
        RawTender(source="ted", source_ref="00999999-2026", title="enkel TED"),
    ]
    assert [t.title for t in drop_ted_duplicates(ted, eproc)] == ["enkel TED"]


def test_extract_description_reads_eprocurement_payload():
    from processor.summarizer import extract_description

    raw = {
        "dossier": {"descriptions": _nl("Dossier-omschrijving")},
        "lots": [{"descriptions": _nl("Dossier-omschrijving")}, {"descriptions": _nl("Perceel 2")}],
    }
    assert extract_description(raw) == "Dossier-omschrijving\n\nPerceel 2"
    assert extract_description({"dossier": {}}) == ""
