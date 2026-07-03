"""Orchestratie van de volledige dagelijkse pijplijn:

scrape (TED) -> upsert -> CPV-filter -> Haiku pre-screen -> Sonnet
samenvatting/score -> digest-selectie -> render -> verzenden (Resend).

Gebruik --dry-run om te scrapen/verwerken en de HTML te renderen naar
out/digest_preview.html zonder te verzenden of tenders als verstuurd te
markeren.
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from database.client import get_client
from database.models import Subscriber, Tender
from mailer.digest_builder import build, format_date_nl
from mailer.sender import send
from processor import cpv_filter, prescreen, summarizer
from scraper.ted_europa import TedSource

logger = logging.getLogger(__name__)

OUT_DIR = Path(__file__).parent.parent / "out"


def scrape_and_store() -> None:
    db = get_client()
    raw_tenders = TedSource().fetch_recent()
    if not raw_tenders:
        logger.info("Geen nieuwe TED-tenders opgehaald")
        return
    rows = [t.to_row() for t in raw_tenders]
    db.table("tenders").upsert(rows, on_conflict="source_ref").execute()
    logger.info("Scraper: %d tenders opgeslagen/bijgewerkt (dedup op source_ref)", len(rows))


def select_digest_candidates() -> list[Tender]:
    db = get_client()
    min_score = int(os.environ.get("MIN_RELEVANCE_SCORE", 6))
    max_count = int(os.environ.get("MAX_TENDERS_PER_DIGEST", 5))

    result = (
        db.table("tenders")
        .select("*")
        .gte("score", min_score)
        .is_("sent_in_digest_at", "null")
        .order("score", desc=True)
        .limit(max_count)
        .execute()
    )
    return [Tender.from_row(row) for row in (result.data or [])]


def get_active_subscribers() -> list[Subscriber]:
    db = get_client()
    result = db.table("subscribers").select("*").eq("active", True).execute()
    return [Subscriber.from_row(row) for row in (result.data or [])]


def mark_sent(tender_ids: list[str]) -> None:
    db = get_client()
    now = datetime.now(timezone.utc).isoformat()
    for tid in tender_ids:
        db.table("tenders").update({"sent_in_digest_at": now}).eq("id", tid).execute()


def run(dry_run: bool) -> None:
    scrape_and_store()
    cpv_filter.run()
    prescreen.run()
    summarizer.run()

    tenders = select_digest_candidates()
    if not tenders:
        logger.info("Geen tenders boven de score-drempel — geen digest verzonden")
        return

    today = datetime.now(timezone.utc).date()

    if dry_run:
        html = build(tenders, today, unsubscribe_url="#")
        OUT_DIR.mkdir(exist_ok=True)
        preview_path = OUT_DIR / "digest_preview.html"
        preview_path.write_text(html, encoding="utf-8")
        logger.info("Dry-run: %d tenders gerenderd naar %s (niet verzonden)", len(tenders), preview_path)
        return

    subscribers = get_active_subscribers()
    if not subscribers:
        logger.warning("Geen actieve subscribers — digest niet verzonden, tenders blijven ongemarkeerd")
        return

    subject = f"Kansenradar — Digest {format_date_nl(today)}"
    sent_count = 0
    for sub in subscribers:
        unsubscribe_url = f"https://kansenradar.be/unsubscribe?token={sub.unsubscribe_token}"
        html = build(tenders, today, unsubscribe_url=unsubscribe_url)
        if send(to=sub.email, subject=subject, html=html):
            sent_count += 1

    mark_sent([t.id for t in tenders])
    logger.info("Digest verzonden naar %d/%d subscribers, %d tenders gemarkeerd als verstuurd", sent_count, len(subscribers), len(tenders))


def main() -> None:
    parser = argparse.ArgumentParser(description="Kansenradar dagelijkse digest-pijplijn")
    parser.add_argument("--dry-run", action="store_true", help="Render naar out/digest_preview.html, verstuur niet")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
