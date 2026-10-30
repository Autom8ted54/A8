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
