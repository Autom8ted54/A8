"""Tests voor mailer.digest_builder — rendering, datums en escaping."""

from datetime import date

from database.models import Tender
from mailer.digest_builder import _deadline_color, build, format_date_nl

TODAY = date(2026, 7, 6)  # maandag


def _tender(**overrides) -> Tender:
    row = {
        "id": "abc-123",
        "source": "ted",
        "source_ref": "00123456-2026",
        "title": "Communicatiecampagne mobiliteit",
        "authority": "Stad Antwerpen",
        "cpv_codes": ["79341000"],
        "budget_text": "€ 85.000",
        "deadline": "2026-08-15",
        "url": "https://ted.europa.eu/x",
        "country": "BE",
        "passed_cpv": True,
        "prescreen_relevant": True,
        "category": "Communicatie",
        "summary": "Korte samenvatting.",
        "score": 8,
        "processed_at": None,
        "sent_in_digest_at": None,
    }
    row.update(overrides)
    return Tender.from_row(row)


def test_format_date_nl():
    assert format_date_nl(TODAY) == "Maandag 6 juli 2026"


def test_deadline_color_urgent_soon_later():
    assert _deadline_color(date(2026, 7, 10), TODAY) == "#DC2626"  # < 14 dagen
    assert _deadline_color(date(2026, 7, 25), TODAY) == "#B45309"  # < 30 dagen
    assert _deadline_color(date(2026, 9, 1), TODAY) == "#15803D"
    assert _deadline_color(None, TODAY) == "#15803D"


def test_build_renders_tender_with_deadline():
    """Regressie: deadline uit Supabase is een string; build() mag niet crashen."""
    html = build([_tender()], TODAY, unsubscribe_url="https://kansenradar.be/u?token=x")
    assert "Communicatiecampagne mobiliteit" in html
    assert "15 augustus 2026" in html
    assert "https://kansenradar.be/u?token=x" in html


def test_build_renders_tender_without_deadline_or_budget():
    html = build([_tender(deadline=None, budget_text=None)], TODAY, unsubscribe_url="#")
    assert "Deadline:" not in html
    assert "Budget:" not in html


def test_build_escapes_html_in_tender_fields():
    """Tender-tekst komt van externe bronnen en AI — moet ge-escaped worden."""
    html = build(
        [_tender(title='<script>alert("x")</script>', summary="<b>bold</b>")],
        TODAY,
        unsubscribe_url="#",
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>bold</b>" not in html


def test_build_singular_plural_intro():
    single = build([_tender()], TODAY, unsubscribe_url="#")
    assert "1 opdracht die" in single
    plural = build([_tender(), _tender(id="2", source_ref="B")], TODAY, unsubscribe_url="#")
    assert "2 opdrachten" in plural
