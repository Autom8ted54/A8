"""Tests voor mailer.run — configuratie-parsing."""

import pytest

from mailer import run
from mailer.run import _env_int


def test_env_int_default_when_missing(monkeypatch):
    monkeypatch.delenv("MIN_RELEVANCE_SCORE", raising=False)
    assert _env_int("MIN_RELEVANCE_SCORE", 6) == 6


def test_env_int_default_when_empty(monkeypatch):
    """GitHub Actions zet een lege string als het secret niet bestaat."""
    monkeypatch.setenv("MIN_RELEVANCE_SCORE", "")
    assert _env_int("MIN_RELEVANCE_SCORE", 6) == 6


def test_env_int_parses_value(monkeypatch):
    monkeypatch.setenv("MAX_TENDERS_PER_DIGEST", "7")
    assert _env_int("MAX_TENDERS_PER_DIGEST", 5) == 7


def test_env_int_raises_on_garbage(monkeypatch):
    monkeypatch.setenv("MAX_TENDERS_PER_DIGEST", "vijf")
    with pytest.raises(ValueError):
        _env_int("MAX_TENDERS_PER_DIGEST", 5)


def test_excluded_refs_parses_and_ignores_blanks(monkeypatch):
    monkeypatch.setenv("DIGEST_EXCLUDE", "A/1, B-2 ,,")
    assert run._excluded_refs() == {"A/1", "B-2"}


def test_excluded_refs_empty(monkeypatch):
    monkeypatch.delenv("DIGEST_EXCLUDE", raising=False)
    assert run._excluded_refs() == set()


def _tender(id_, source, title, score=7):
    from database.models import Tender

    return Tender(
        id=id_, source=source, source_ref=id_, title=title, authority=None, cpv_codes=[],
        budget_text=None, deadline=None, url=None, country="BE", passed_cpv=True,
        prescreen_relevant=True, category=None, summary=None, score=score,
        processed_at=None, sent_in_digest_at=None,
    )


def test_dedupe_prefers_eprocurement_and_keeps_order():
    ted_a = _tender("t1", "ted", "België – Reclamediensten – Campagne Verkeersquiz VSV", score=8)
    ted_b = _tender("t2", "ted", "België – Reclamediensten – Campagne Verkeersquiz VSV", score=7)
    other = _tender("o1", "e-procurement", "Website stad Nieuwpoort", score=7)
    eproc = _tender("e1", "e-procurement", "Campagne Verkeersquiz VSV", score=6)
    kept, dupes = run.dedupe_by_title([ted_a, ted_b, other, eproc])
    assert [t.id for t in kept] == ["o1", "e1"]
    assert {t.id for t in dupes} == {"t1", "t2"}
