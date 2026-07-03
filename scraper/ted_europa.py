"""TED (Tenders Electronic Daily) scraper — EU-brede aanbestedingen.

Open JSON search-API, geen API-key nodig. Contract geverifieerd via curl
tegen https://api.ted.europa.eu/v3/notices/search (2026-07-03):
- Expert query-taal: "veld IN (...) AND veld IN (...) SORT BY veld DESC" als
  losse string in "query", geen apart "sort"-veld.
- Relatieve datumfilter: "publication-date >= today(-N)".
- "fields" bepaalt welke datavelden terugkomen; "links" (incl. html.NLD) komt
  altijd mee, ook zonder expliciete aanvraag.
- Meertalige velden (notice-title, organisation-name-buyer) komen terug als
  dict per taalcode (bv. "nld", "eng", "fra").
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime

import requests

from database.models import RawTender
from scraper.base import Source

logger = logging.getLogger(__name__)

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"

# CPV-codes marketing & communicatie (zie CLAUDE.md)
CPV_CODES = [
    "79340000",  # Reclame- en marketingdiensten
    "79341000",  # Reclamediensten
    "79342000",  # Marketingdiensten
    "79416000",  # Public relationsdiensten
    "79952000",  # Evenementendiensten
    "72413000",  # Websiteontwerpdiensten
]

FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "organisation-name-buyer",
    "deadline-receipt-request-date-lot",
    "deadline-receipt-tender-date-lot",
    "classification-cpv",
    "description-proc",
    "description-lot",
]

# Hoeveel dagen terug scannen — ruim boven de dagelijkse cron-cadans om
# gemiste runs (weekend, storing) op te vangen. Dedup gebeurt op source_ref.
LOOKBACK_DAYS = 3

PREFERRED_LANGS = ("nld", "eng", "fra")


def _pick_lang(value: dict | None) -> str | None:
    """Kies NL, val terug op EN/FR, anders eerste beschikbare waarde."""
    if not value:
        return None
    for lang in PREFERRED_LANGS:
        if lang in value:
            v = value[lang]
            return v[0] if isinstance(v, list) else v
    first = next(iter(value.values()), None)
    return first[0] if isinstance(first, list) else first


def _parse_date(value: str | None) -> date | None:
    """TED-datums hebben formaat '2026-07-10+02:00'."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        logger.warning("Kon TED-datum niet parsen: %r", value)
        return None


class TedSource(Source):
    name = "ted"

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    def fetch_recent(self) -> list[RawTender]:
        cpv_list = ", ".join(CPV_CODES)
        query = (
            f"classification-cpv IN ({cpv_list}) "
            f"AND place-of-performance IN (BEL) "
            f"AND publication-date >= today(-{LOOKBACK_DAYS}) "
            f"SORT BY publication-date DESC"
        )

        tenders: list[RawTender] = []
        page = 1
        page_size = 100
        while True:
            payload = {"query": query, "fields": FIELDS, "page": page, "limit": page_size}
            resp = self.session.post(TED_SEARCH_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if data.get("message"):
                raise RuntimeError(f"TED API-fout: {data['message']}")

            notices = data.get("notices", [])
            for notice in notices:
                tenders.append(self._to_raw_tender(notice))

            total = data.get("totalNoticeCount", 0)
            if page * page_size >= total or not notices:
                break
            page += 1

        logger.info("TED: %d tenders opgehaald (laatste %d dagen, BE, CPV-filter)", len(tenders), LOOKBACK_DAYS)
        return tenders

    def _to_raw_tender(self, notice: dict) -> RawTender:
        pub_number = notice["publication-number"]
        deadline_raw = notice.get("deadline-receipt-request-date-lot") or notice.get(
            "deadline-receipt-tender-date-lot"
        )
        deadline_str = deadline_raw[0] if isinstance(deadline_raw, list) and deadline_raw else deadline_raw

        cpv_codes = notice.get("classification-cpv") or []
        # dedupliceren met behoud van volgorde (TED retourneert soms duplicaten)
        cpv_codes = list(dict.fromkeys(cpv_codes))

        url = notice.get("links", {}).get("html", {}).get("NLD") or notice.get("links", {}).get(
            "html", {}
        ).get("ENG")

        return RawTender(
            source=self.name,
            source_ref=pub_number,
            title=_pick_lang(notice.get("notice-title")) or "(geen titel)",
            authority=_pick_lang(notice.get("organisation-name-buyer")),
            cpv_codes=cpv_codes,
            budget_text=None,  # TED-waardevelden vergen aparte BT-mapping; nog niet ontsloten
            deadline=_parse_date(deadline_str),
            url=url,
            country="BE",
            raw=notice,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for t in TedSource().fetch_recent():
        print(f"{t.source_ref} | {t.deadline} | {t.title} | {t.authority} | {t.url}")
