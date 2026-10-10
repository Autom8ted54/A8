"""Enrich companies by enterprise number from the local KBO Open Data export (a8leads project).

Fills naam, website, email (source 'KBO-ENT' / 'KBO-EST'), gemeente, postcode and main NACE code.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

KBO_DIR = Path.home() / "a8leads/data/KboOpenData_0420_2026_07_14_Full"


def _dotted(kbo: str) -> str:
    return f"{kbo[:4]}.{kbo[4:7]}.{kbo[7:]}"


def _rows(name: str):
    with (KBO_DIR / name).open(encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def enrich(companies: dict[str, dict]) -> None:
    """Mutates companies (keyed by 10-digit KBO number) in place; existing values win."""
    wanted = {_dotted(k): k for k in companies}

    est_to_ent = {}
    for r in _rows("establishment.csv"):
        if r["EnterpriseNumber"] in wanted:
            est_to_ent[r["EstablishmentNumber"]] = wanted[r["EnterpriseNumber"]]

    for r in _rows("denomination.csv"):
        kbo = wanted.get(r["EntityNumber"])
        # 001 = official name, 003 = commercial name; prefer commercial for outreach
        if kbo and r["TypeOfDenomination"] in ("001", "003"):
            c = companies[kbo]
            if r["TypeOfDenomination"] == "003" or not c.get("naam"):
                c["naam"] = r["Denomination"]

    for r in _rows("contact.csv"):
        ent = wanted.get(r["EntityNumber"]) or est_to_ent.get(r["EntityNumber"])
        if not ent:
            continue
        c = companies[ent]
        value = r["Value"].strip()
        if r["ContactType"] == "WEB" and not c.get("website"):
            c["website"] = value
        elif r["ContactType"] == "EMAIL" and not c.get("email"):
            c["email"] = value.lower()
            c["email_bron"] = "KBO-ENT" if r["EntityContact"] == "ENT" else "KBO-EST"

    for r in _rows("address.csv"):
        kbo = wanted.get(r["EntityNumber"])
        if kbo and r["TypeOfAddress"] == "REGO" and not companies[kbo].get("gemeente"):
            companies[kbo]["gemeente"] = r["MunicipalityNL"] or r["MunicipalityFR"]
            companies[kbo]["postcode"] = r["Zipcode"]

    for r in _rows("activity.csv"):
        kbo = wanted.get(r["EntityNumber"])
        if kbo and r["Classification"] == "MAIN" and (r["NaceVersion"] == "2025" or not companies[kbo].get("nace_code")):
            companies[kbo]["nace_code"] = r["NaceCode"]

    logger.info("KBO enrich: %d companies", len(companies))
