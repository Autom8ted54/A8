"""CPV-filter — exacte controle op relevante CPV-codes (geen AI, gratis).

De TED-scraper query filtert al grof op CPV; deze stap is de precieze
prefix-match en is herbruikbaar voor bronnen (bv. e-notification) die geen
CPV-query ondersteunen.
"""

from __future__ import annotations

import logging

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


def matches(cpv_codes: list[str]) -> bool:
    """True als minstens 1 CPV-code onder de relevante prefixen valt."""
    return any(code.startswith(CPV_PREFIXES) for code in cpv_codes)


def run() -> int:
    """Zet passed_cpv op alle tenders waar dat nog niet bepaald is.

    Returns het aantal verwerkte rijen.
    """
    client = get_client()
    result = client.table("tenders").select("id, cpv_codes").is_("passed_cpv", "null").execute()
    rows = result.data or []

    for row in rows:
        passed = matches(row.get("cpv_codes") or [])
        client.table("tenders").update({"passed_cpv": passed}).eq("id", row["id"]).execute()

    logger.info("CPV-filter: %d tenders beoordeeld", len(rows))
    return len(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
