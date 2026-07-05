"""Tests voor scraper.ted_europa — parsing van TED-notices, zonder netwerk."""

from datetime import date
from unittest.mock import MagicMock

from scraper.ted_europa import TedSource, _parse_date, _pick_lang

SAMPLE_NOTICE = {
    "publication-number": "00123456-2026",
    "publication-date": "2026-07-03+02:00",
    "notice-title": {"nld": "Communicatiecampagne", "eng": "Communication campaign"},
    "organisation-name-buyer": {"nld": ["Stad Gent"]},
    "deadline-receipt-tender-date-lot": ["2026-08-15+02:00"],
    "classification-cpv": ["79341000", "79341000", "79342000"],
    "links": {"html": {"NLD": "https://ted.europa.eu/nl/x", "ENG": "https://ted.europa.eu/en/x"}},
}


def test_pick_lang_prefers_dutch():
    assert _pick_lang({"eng": "EN", "nld": "NL"}) == "NL"


def test_pick_lang_falls_back_to_english():
    assert _pick_lang({"eng": "EN", "deu": "DE"}) == "EN"


def test_pick_lang_falls_back_to_first_available():
    assert _pick_lang({"deu": "DE"}) == "DE"


def test_pick_lang_unwraps_lists():
    assert _pick_lang({"nld": ["NL"]}) == "NL"


def test_pick_lang_handles_none_and_empty():
    assert _pick_lang(None) is None
    assert _pick_lang({}) is None


def test_parse_date_with_ted_offset_format():
    assert _parse_date("2026-07-10+02:00") == date(2026, 7, 10)


def test_parse_date_invalid_returns_none():
    assert _parse_date("geen datum") is None
    assert _parse_date(None) is None


def test_to_raw_tender_maps_fields():
    t = TedSource()._to_raw_tender(SAMPLE_NOTICE)
    assert t.source == "ted"
    assert t.source_ref == "00123456-2026"
    assert t.title == "Communicatiecampagne"
    assert t.authority == "Stad Gent"
    assert t.deadline == date(2026, 8, 15)
    assert t.url == "https://ted.europa.eu/nl/x"
    assert t.cpv_codes == ["79341000", "79342000"]  # gededupliceerd, volgorde behouden


def test_to_raw_tender_handles_minimal_notice():
    t = TedSource()._to_raw_tender({"publication-number": "X-2026"})
    assert t.title == "(geen titel)"
    assert t.authority is None
    assert t.deadline is None
    assert t.url is None
    assert t.cpv_codes == []


def _mock_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_fetch_recent_paginates_until_total():
    session = MagicMock()
    page1 = {"notices": [SAMPLE_NOTICE] * 100, "totalNoticeCount": 150}
    page2 = {"notices": [SAMPLE_NOTICE] * 50, "totalNoticeCount": 150}
    session.post.side_effect = [_mock_response(page1), _mock_response(page2)]

    tenders = TedSource(session=session).fetch_recent()
    assert len(tenders) == 150
    assert session.post.call_count == 2


def test_fetch_recent_stops_on_empty_page():
    session = MagicMock()
    session.post.return_value = _mock_response({"notices": [], "totalNoticeCount": 0})
    assert TedSource(session=session).fetch_recent() == []
    assert session.post.call_count == 1
