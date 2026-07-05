"""Tests voor database.models — vooral het parsen van Supabase-rijen."""

from datetime import date, datetime

from database.models import RawTender, Subscriber, Tender


def _tender_row(**overrides) -> dict:
    row = {
        "id": "abc-123",
        "source": "ted",
        "source_ref": "00123456-2026",
        "title": "Communicatiecampagne",
        "authority": "Stad Antwerpen",
        "cpv_codes": ["79341000"],
        "budget_text": None,
        "deadline": "2026-08-15",
        "url": "https://ted.europa.eu/x",
        "country": "BE",
        "passed_cpv": True,
        "prescreen_relevant": True,
        "category": "Communicatie",
        "summary": "Samenvatting.",
        "score": 8,
        "processed_at": "2026-07-05T06:12:00+00:00",
        "sent_in_digest_at": None,
    }
    row.update(overrides)
    return row


def test_tender_from_row_parses_deadline_string_to_date():
    t = Tender.from_row(_tender_row())
    assert t.deadline == date(2026, 8, 15)
    assert isinstance(t.deadline, date)


def test_tender_from_row_handles_null_deadline():
    t = Tender.from_row(_tender_row(deadline=None))
    assert t.deadline is None


def test_tender_from_row_parses_timestamps():
    t = Tender.from_row(_tender_row())
    assert isinstance(t.processed_at, datetime)
    assert t.sent_in_digest_at is None


def test_tender_from_row_defaults_cpv_codes_to_empty_list():
    t = Tender.from_row(_tender_row(cpv_codes=None))
    assert t.cpv_codes == []


def test_raw_tender_to_row_serializes_deadline():
    rt = RawTender(
        source="ted",
        source_ref="X",
        title="T",
        deadline=date(2026, 8, 15),
    )
    row = rt.to_row()
    assert row["deadline"] == "2026-08-15"


def test_raw_tender_to_row_handles_missing_deadline():
    rt = RawTender(source="ted", source_ref="X", title="T")
    assert rt.to_row()["deadline"] is None


def test_subscriber_from_row():
    s = Subscriber.from_row(
        {
            "id": "1",
            "email": "a@b.be",
            "naam": None,
            "plan": "founding",
            "active": True,
            "unsubscribe_token": "tok",
        }
    )
    assert s.email == "a@b.be"
    assert s.active is True
