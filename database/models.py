"""Data models voor de tender-pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class RawTender:
    """Genormaliseerd resultaat van een scraper, vóór opslag in Supabase."""

    source: str  # 'ted' | 'e-notification'
    source_ref: str
    title: str
    authority: str | None = None
    cpv_codes: list[str] = field(default_factory=list)
    budget_text: str | None = None
    deadline: date | None = None
    url: str | None = None
    country: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        """Naar Supabase-insert-formaat (kolomnamen van de `tenders`-tabel)."""
        return {
            "source": self.source,
            "source_ref": self.source_ref,
            "title": self.title,
            "authority": self.authority,
            "cpv_codes": self.cpv_codes,
            "budget_text": self.budget_text,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "url": self.url,
            "country": self.country,
            "raw": self.raw,
        }


@dataclass
class Tender:
    """Volledige tender-rij zoals opgeslagen in Supabase, incl. verwerkingsstatus."""

    id: str
    source: str
    source_ref: str
    title: str
    authority: str | None
    cpv_codes: list[str]
    budget_text: str | None
    deadline: date | None
    url: str | None
    country: str | None
    passed_cpv: bool | None
    prescreen_relevant: bool | None
    category: str | None
    summary: str | None
    score: int | None
    processed_at: datetime | None
    sent_in_digest_at: datetime | None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Tender":
        return cls(
            id=row["id"],
            source=row["source"],
            source_ref=row["source_ref"],
            title=row["title"],
            authority=row.get("authority"),
            cpv_codes=row.get("cpv_codes") or [],
            budget_text=row.get("budget_text"),
            deadline=row.get("deadline"),
            url=row.get("url"),
            country=row.get("country"),
            passed_cpv=row.get("passed_cpv"),
            prescreen_relevant=row.get("prescreen_relevant"),
            category=row.get("category"),
            summary=row.get("summary"),
            score=row.get("score"),
            processed_at=row.get("processed_at"),
            sent_in_digest_at=row.get("sent_in_digest_at"),
        )


@dataclass
class Subscriber:
    id: str
    email: str
    naam: str | None
    plan: str | None
    active: bool
    unsubscribe_token: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Subscriber":
        return cls(
            id=row["id"],
            email=row["email"],
            naam=row.get("naam"),
            plan=row.get("plan"),
            active=row.get("active", True),
            unsubscribe_token=row["unsubscribe_token"],
        )
