"""CPV-filter — exacte controle op relevante CPV-codes + event-zoekwoorden (geen AI, gratis).

De TED-scraper query filtert al grof op CPV; deze stap is de precieze
prefix-match en is herbruikbaar voor bronnen (bv. e-notification) die geen
CPV-query ondersteunen.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from database.client import get_client

logger = logging.getLogger(__name__)

# Prefix van 5 cijfers = subcategorie-niveau. Matcht bv. 79340000 op
# 79341400, 79342300, ... (TED-notices geven vaak een specifiekere code
# binnen dezelfde categorie dan de 8-cijferige hoofdcode).
CPV_PREFIXES = (
    "79340",  # Reclame- en marketingdiensten
    "79341",  # Reclamediensten
    "79342",  # Marketingdiensten
    "79416",  # Public relationsdiensten
    "79952",  # Evenementendiensten
    "72413",  # Websiteontwerpdiensten
)


# Events die onder een andere CPV-code staan (bv. "logistiek" of "organisatie"),
# zie FAQ op de site. Matcht op titel/omschrijving zonder accenten; de Haiku-
# prescreen vangt nadien de vals positieven op. Bewust geen kaal "event":
# dat matcht ook "eventueel".
EVENT_KEYWORDS = re.compile(
    r"evenement"            # evenement(en), evenementiele, evenementen-
    r"|\bevents?\b"
    r"|congres|colloqu|symposi|seminar"
    r"|festival|infodag|opendeurdag|beursstand|standenbouw|vakbeurs|handelsbeurs"
    r"|\bsalon\b|inauguration|inhuldiging",
)


def _normalize(text: str) -> str:
    """Kleine letters zonder accenten ('Événement' -> 'evenement')."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def matches(cpv_codes: list[str]) -> bool:
    """True als minstens 1 CPV-code onder de relevante prefixen valt."""
    return any(code.startswith(CPV_PREFIXES) for code in cpv_codes)


def matches_event_keywords(*texts: str | None) -> bool:
    """True als titel of omschrijving duidelijk over een evenement gaat."""
    return any(EVENT_KEYWORDS.search(_normalize(t)) for t in texts if t)


def is_relevant(cpv_codes: list[str], title: str | None, description: str | None = None) -> bool:
    return matches(cpv_codes) or matches_event_keywords(title, description)


def run() -> int:
    """Zet passed_cpv op alle tenders waar dat nog niet bepaald is.

    Returns het aantal verwerkte rijen.
    """
    client = get_client()
    from processor.summarizer import extract_description

    result = client.table("tenders").select("id, cpv_codes, title, raw").is_("passed_cpv", "null").execute()
    rows = result.data or []

    passed_ids = [
        row["id"]
        for row in rows
        if is_relevant(row.get("cpv_codes") or [], row.get("title"), extract_description(row.get("raw") or {}))
    ]
    failed_ids = [row["id"] for row in rows if row["id"] not in set(passed_ids)]

    if passed_ids:
        client.table("tenders").update({"passed_cpv": True}).in_("id", passed_ids).execute()
    if failed_ids:
        client.table("tenders").update({"passed_cpv": False}).in_("id", failed_ids).execute()

    logger.info("CPV-filter: %d tenders beoordeeld (%d relevant)", len(rows), len(passed_ids))
    return len(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
