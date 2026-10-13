"""Tests for outreach.send: template parsing, warm-up and planning, inbound classification."""

import json
from datetime import date
from email.message import EmailMessage

import pytest

from outreach.send import (
    classify_inbound,
    clean_name,
    daily_limit,
    load_templates,
    pick_example,
    plan_today,
    render,
    render_html,
)

MONDAY = date(2026, 11, 2)


def _row(email, golf="A", naam="Bureau X NV"):
    return {"email": email, "golf": golf, "naam": naam}


def _state(prospects=None, first_send=None, sent_per_day=None):
    return {"first_send": first_send, "sent_per_day": sent_per_day or {}, "prospects": prospects or {}}


def test_templates_parse_all_six_mails():
    t = load_templates()
    assert set(t) == {"A1", "A2", "A3", "B1", "B2", "B3"}
    assert t["A1"].body.startswith("Beste,")
    assert "?bron=b2" in t["B2"].body and "?bron=a2" not in t["B2"].body
    assert t["B3"].subject == "Re: " + t["B1"].subject


EXAMPLE = {
    "title": "Raamovereenkomst omgevingscommunicatie", "authority": "Stad Hasselt", "score": 9,
    "budget_text": None, "deadline": "2026-11-20", "url": "https://ted.europa.eu/x",
    "summary": "Stad Hasselt zoekt partners voor communicatie. Tweede zin.",
}


def test_render_fills_name_and_example_everywhere():
    for key in ("A1", "B1"):
        t = render(load_templates()[key], "Studio Zuid", EXAMPLE)
        assert "{naam}" not in t.subject + t.body and "{voorbeeld}" not in t.body
        assert "Studio Zuid" in t.subject
        assert "Stad Hasselt · deadline 20 november 2026" in t.body
        assert "Tweede zin" not in t.body


def test_html_version_has_card_logo_and_links():
    h = render_html(load_templates()["A1"], "Studio <Zuid>", EXAMPLE)
    assert "Studio &lt;Zuid&gt;" in h
    assert "logo-mail.png" in h and "border-left:3px solid #F5A623" in h
    assert 'href="https://kansenradar.be/?bron=a1"' in h
    assert "{voorbeeld}" not in h


def test_pick_example_skips_tenders_closing_within_a_week(tmp_path):
    f = tmp_path / "t.json"
    f.write_text(json.dumps([
        {**EXAMPLE, "score": 10, "deadline": "2026-11-05"},
        {**EXAMPLE, "score": 8, "deadline": "2026-11-30"},
    ]))
    assert pick_example(MONDAY, f)["score"] == 8
    with pytest.raises(SystemExit):
        pick_example(date(2026, 12, 1), f)


def test_clean_name():
    assert clean_name("Onlyhumans NV") == "Onlyhumans"
    assert clean_name("CRONOS PUBLIC SERVICES") == "Cronos Public Services"
    assert clean_name("VRT") == "VRT"


def test_warmup_grows_and_caps():
    assert daily_limit(None, MONDAY) == 10
    assert daily_limit(MONDAY, date(2026, 11, 5)) == 16
    assert daily_limit(MONDAY, date(2026, 12, 31)) == 40


def test_weekend_sends_nothing():
    assert plan_today([_row("a@x.be")], _state(), date(2026, 11, 7)) == []


def test_wave_a_before_b_and_limit():
    rows = [_row(f"b{i}@x.be", "B") for i in range(20)] + [_row("a@x.be", "A")]
    plan = plan_today(rows, _state(), MONDAY)
    assert len(plan) == 10
    assert plan[0][0] == "a@x.be"


def test_followup_due_on_day_4_and_skips_stopped():
    sent = [{"step": 1, "date": "2026-10-29", "message_id": "<1@k>"}]
    prospects = {
        "due@x.be": {"status": "active", "sent": sent, "row": _row("due@x.be")},
        "stop@x.be": {"status": "stopped", "sent": sent, "row": _row("stop@x.be")},
    }
    plan = plan_today([], _state(prospects, "2026-10-29"), MONDAY)
    assert [(a, s) for a, s, _ in plan] == [("due@x.be", 2)]


def test_no_followup_after_step_3():
    sent = [{"step": n, "date": "2026-10-01", "message_id": f"<{n}@k>"} for n in (1, 2, 3)]
    prospects = {"done@x.be": {"status": "active", "sent": sent, "row": _row("done@x.be")}}
    assert plan_today([], _state(prospects, "2026-10-01"), MONDAY) == []


def test_already_sent_today_counts_toward_limit():
    rows = [_row(f"b{i}@x.be", "B") for i in range(20)]
    state = _state(first_send=MONDAY.isoformat(), sent_per_day={MONDAY.isoformat(): 7})
    assert len(plan_today(rows, state, MONDAY)) == 3


def _msg(sender, body, subject="Re: Overheidsopdrachten", in_reply_to=""):
    m = EmailMessage()
    m["From"] = sender
    m["Subject"] = subject
    if in_reply_to:
        m["In-Reply-To"] = in_reply_to
    m.set_content(body)
    return m


def test_classify_stop_reply_and_bounce():
    known = {"jan@bureau.be"}
    ids = {"<1@k>": "jan@bureau.be"}
    assert classify_inbound(_msg("Jan <jan@bureau.be>", "Stop aub"), known, ids) == ("jan@bureau.be", "stopped")
    assert classify_inbound(_msg("Jan <jan@bureau.be>", "Klinkt goed, vertel meer"), known, ids) == ("jan@bureau.be", "replied")
    # Reply from a colleague's address, matched through the thread id
    assert classify_inbound(_msg("an@bureau.be", "Interessant", in_reply_to="<1@k>"), known, ids) == ("jan@bureau.be", "replied")
    bounce = _msg("MAILER-DAEMON@mail.x", "Delivery to jan@bureau.be failed", subject="Undelivered Mail")
    assert classify_inbound(bounce, known, ids) == ("jan@bureau.be", "bounced")
    assert classify_inbound(_msg("random@spam.com", "hello"), known, ids) is None


def test_stop_in_quoted_original_is_not_a_stop():
    body = "Graag meer info.\n> Geen interesse? Antwoord \"stop\" en je hoort niets meer van ons."
    assert classify_inbound(_msg("jan@bureau.be", body), {"jan@bureau.be"}, {}) == ("jan@bureau.be", "replied")


def test_outlook_style_quote_is_not_a_stop():
    body = "Graag meer info.\n\nVan: Filip <filip@kansenradar.eu>\nGeen interesse? Antwoord \"stop\"."
    assert classify_inbound(_msg("jan@bureau.be", body), {"jan@bureau.be"}, {}) == ("jan@bureau.be", "replied")
