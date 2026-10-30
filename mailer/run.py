"""Orchestratie van de volledige dagelijkse pijplijn:

scrape (TED + e-Procurement) -> upsert -> CPV-filter -> Haiku pre-screen -> Sonnet
samenvatting/score -> digest-selectie -> render -> verzenden (Resend).

Gebruik --dry-run om te scrapen/verwerken en de HTML te renderen naar
out/digest_preview.html zonder te verzenden of tenders als verstuurd te
markeren.

Review-flow (zie workflow): --preview mailt zondag een voorbeeld naar Filip,
--send verstuurt maandag wat er klaarstaat (zonder opnieuw te scrapen), tenzij
DIGEST_HOLD=true. DIGEST_EXCLUDE (komma-gescheiden source_refs) houdt opdrachten
uit de digest.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from database.client import get_client
from database.models import RawTender, Subscriber, Tender
from mailer.digest_builder import build, format_date_nl
from mailer.sender import send
from processor import cpv_filter, prescreen, summarizer
from scraper.e_procurement import EProcurementSource, ted_number_key
from scraper.ted_europa import TedSource

logger = logging.getLogger(__name__)

OUT_DIR = Path(__file__).parent.parent / "out"

# Resend free tier laat 2 requests/seconde toe
SEND_INTERVAL_SECONDS = 0.6


def _env_int(name: str, default: int) -> int:
    """Als een GitHub secret niet bestaat, komt de env var als lege string binnen."""
    value = os.environ.get(name, "").strip()
    return int(value) if value else default


def drop_ted_duplicates(ted: list[RawTender], eproc: list[RawTender]) -> list[RawTender]:
    """Laat TED-notices vallen die e-Procurement al heeft (Belgische publicaties
    gaan via e-Procurement naar TED). De e-Procurement-versie wint: NL-titel,
    deadline en link naar het Belgische platform."""
    known = {
        key
        for t in eproc
        for ref in t.raw.get("publicationReferenceNumbersTED") or []
        if (key := ted_number_key(ref))
    }
    kept = [t for t in ted if ted_number_key(t.source_ref) not in known]
    if len(kept) < len(ted):
        logger.info("Dedup: %d TED-notices overgeslagen (al via e-Procurement)", len(ted) - len(kept))
    return kept


def scrape_and_store() -> list[str]:
    """Scrape alle bronnen en sla op. Geeft de namen van gefaalde bronnen terug,
    zodat één kapotte bron de digest niet tegenhoudt maar wel een alert geeft."""
    db = get_client()
    failed: list[str] = []

    eproc_tenders: list[RawTender] = []
    try:
        eproc = EProcurementSource.from_env()
        if eproc is None:
            logger.info("e-Procurement niet geconfigureerd (EPROC_ENV leeg) — overgeslagen")
        else:
            eproc_tenders = eproc.fetch_recent()
    except Exception:
        logger.exception("e-Procurement-scraper gefaald")
        failed.append("e-procurement")

    ted_tenders: list[RawTender] = []
    try:
        ted_tenders = TedSource().fetch_recent()
    except Exception:
        logger.exception("TED-scraper gefaald")
        failed.append("ted")

    raw_tenders = eproc_tenders + drop_ted_duplicates(ted_tenders, eproc_tenders)
    if not raw_tenders:
        logger.info("Geen nieuwe tenders opgehaald")
        return failed
    rows = [t.to_row() for t in raw_tenders]
    # ignore_duplicates: bestaande rijen niet overschrijven — de lookback zou
    # anders AI-velden (budget_text) en verwerkingsstatus wissen.
    db.table("tenders").upsert(rows, on_conflict="source_ref", ignore_duplicates=True).execute()
    logger.info("Scraper: %d tenders opgeslagen (dedup op source_ref)", len(rows))
    return failed


def select_digest_candidates() -> list[Tender]:
    db = get_client()
    min_score = _env_int("MIN_RELEVANCE_SCORE", 6)
    max_count = _env_int("MAX_TENDERS_PER_DIGEST", 5)
    today_iso = datetime.now(timezone.utc).date().isoformat()

    excluded = _excluded_refs()

    # Ruimer ophalen en in Python filteren, zodat uitgesloten opdrachten opschuiven
    result = (
        db.table("tenders")
        .select("*")
        .gte("score", min_score)
        .is_("sent_in_digest_at", "null")
        .or_(f"deadline.is.null,deadline.gte.{today_iso}")
        .order("score", desc=True)
        .limit(max_count + len(excluded))
        .execute()
    )
    tenders = [Tender.from_row(row) for row in (result.data or [])]
    return [t for t in tenders if t.source_ref not in excluded][:max_count]


def _excluded_refs() -> set[str]:
    raw = os.environ.get("DIGEST_EXCLUDE", "")
    return {ref.strip() for ref in raw.split(",") if ref.strip()}


def get_active_subscribers() -> list[Subscriber]:
    db = get_client()
    result = db.table("subscribers").select("*").eq("active", True).execute()
    return [Subscriber.from_row(row) for row in (result.data or [])]


def mark_sent(tender_ids: list[str]) -> None:
    db = get_client()
    now = datetime.now(timezone.utc).isoformat()
    db.table("tenders").update({"sent_in_digest_at": now}).in_("id", tender_ids).execute()


def run(dry_run: bool, mode: str = "full") -> None:
    """mode: full = scrapen + verwerken + verzenden; preview = scrapen + verwerken +
    voorbeeld naar Filip; send = enkel verwerken wat er ligt + verzenden."""
    if mode == "send" and os.environ.get("DIGEST_HOLD", "").strip().lower() == "true":
        logger.warning("DIGEST_HOLD=true — digest niet verzonden")
        return
    failed_sources = [] if mode == "send" else scrape_and_store()
    _process_and_send(dry_run, preview=(mode == "preview"))
    if failed_sources:
        # Pas na de digest falen, zodat de workflow-alert afgaat
        raise RuntimeError(f"Bron(nen) gefaald: {', '.join(failed_sources)}")


def _send_preview(tenders: list[Tender], today) -> None:
    """Mail het voorbeeld naar Filip, met de source_refs erbij om uit te sluiten."""
    to = os.environ.get("PREVIEW_EMAIL", "").strip() or "hallo@kansenradar.be"
    rows = "".join(
        f"<li>{t.score} — {t.title[:90]} — <code>{t.source_ref}</code></li>" for t in tenders
    )
    banner = (
        '<div style="font:14px/1.5 sans-serif;background:#fff6d6;padding:12px 16px;margin:0 0 12px">'
        "<strong>Voorbeeld — nog niet verzonden.</strong> Zonder actie gaat dit maandag 07:00 uit "
        "naar de abonnees. Uitsluiten: zet de code in de GitHub-variabele DIGEST_EXCLUDE. "
        f"Alles tegenhouden: DIGEST_HOLD = true.<ol>{rows}</ol></div>"
    )
    html = build(tenders, today, unsubscribe_url="#")
    html = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + banner, html, count=1)
    if not send(to=to, subject=f"[Voorbeeld] Kansenradar — Digest {format_date_nl(today)}", html=html):
        raise RuntimeError("Voorbeeld-mail versturen mislukt")
    logger.info("Voorbeeld van %d tenders gemaild naar %s", len(tenders), to)


def _process_and_send(dry_run: bool, preview: bool = False) -> None:
    cpv_filter.run()
    prescreen.run()
    summarizer.run()

    tenders = select_digest_candidates()
    if not tenders:
        logger.info("Geen tenders boven de score-drempel — geen digest verzonden")
        return

    today = datetime.now(timezone.utc).date()

    if preview:
        if dry_run:
            logger.info("Preview + dry-run: %d tenders, geen mail", len(tenders))
        else:
            _send_preview(tenders, today)
        return

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
    for i, sub in enumerate(subscribers):
        if i > 0:
            time.sleep(SEND_INTERVAL_SECONDS)
        unsubscribe_url = f"https://kansenradar.be/unsubscribe?token={sub.unsubscribe_token}"
        html = build(tenders, today, unsubscribe_url=unsubscribe_url)
        if send(to=sub.email, subject=subject, html=html, unsubscribe_url=unsubscribe_url):
            sent_count += 1

    if sent_count == 0:
        logger.error(
            "Geen enkele verzending gelukt (%d subscribers) — tenders blijven ongemarkeerd voor morgen",
            len(subscribers),
        )
        return

    mark_sent([t.id for t in tenders])
    logger.info("Digest verzonden naar %d/%d subscribers, %d tenders gemarkeerd als verstuurd", sent_count, len(subscribers), len(tenders))


def main() -> None:
    parser = argparse.ArgumentParser(description="Kansenradar dagelijkse digest-pijplijn")
    parser.add_argument("--dry-run", action="store_true", help="Render naar out/digest_preview.html, verstuur niet")
    parser.add_argument("--preview", action="store_true", help="Mail een voorbeeld naar Filip, verstuur niet naar abonnees")
    parser.add_argument("--send", action="store_true", help="Verstuur wat er klaarstaat, zonder opnieuw te scrapen")
    args = parser.parse_args()
    mode = "preview" if args.preview else "send" if args.send else "full"

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    run(dry_run=args.dry_run, mode=mode)


if __name__ == "__main__":
    main()
