"""Build a prospect list of Belgian agencies that won Belgian marketing/communication tenders.

Source: TED contract award notices (last 3 years, place of performance BE, marketing CPV codes).
Per notice the API gives winner enterprise numbers; the notice XML gives name, website, city and
sometimes an e-mail per organisation. Websites are then verified via the KBO number
(outreach.verify_prospects.check) and real addresses harvested.

Run: uv run python -m outreach.ted_winners
Output: outreach/state/ted_winners.csv (gitignored)
"""

from __future__ import annotations

import csv
import logging
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from outreach import kbo_enrich
from outreach.verify_prospects import check

logger = logging.getLogger(__name__)

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"
OUTPUT = Path(__file__).parent / "state" / "ted_winners.csv"
LOOKBACK_DAYS = 3 * 365

# Marketing & communication family incl. common sub-codes (TED matches exact codes)
CPV_CODES = [
    "79340000", "79341000", "79341100", "79341200", "79341400", "79341500",
    "79342000", "79342100", "79342200", "79342300", "79342310", "79342320", "79342400",
    "79416000", "79416100", "79416200",
    "79952000", "79952100", "79950000", "79951000", "79956000",
    "72413000", "79822500", "79413000",
]

NS = {
    "efac": "http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


def _kbo(value: str | None) -> str | None:
    """Normalize a Belgian enterprise number to 10 digits ('BE 0123.456.789' -> '0123456789')."""
    if not value:
        return None
    digits = re.sub(r"\D", "", value.split("_")[0])
    if len(digits) == 9:
        digits = "0" + digits
    return digits if len(digits) == 10 and digits[0] in "01" else None


def fetch_award_notices(session: requests.Session) -> list[dict]:
    query = (
        f"classification-cpv IN ({', '.join(CPV_CODES)}) AND place-of-performance IN (BEL) "
        f"AND notice-type IN (can-standard, can-social) AND publication-date >= today(-{LOOKBACK_DAYS}) "
        f"SORT BY publication-date DESC"
    )
    notices, page = [], 1
    while True:
        payload = {
            "query": query,
            "fields": ["publication-number", "publication-date", "winner-identifier", "winner-country", "notice-title"],
            "page": page,
            "limit": 100,
        }
        data = session.post(TED_SEARCH_URL, json=payload, timeout=60).json()
        if data.get("message"):
            raise RuntimeError(f"TED API error: {data['message']}")
        batch = data.get("notices", [])
        notices += batch
        if page * 100 >= data.get("totalNoticeCount", 0) or not batch:
            break
        page += 1
    logger.info("TED: %d award notices", len(notices))
    return notices


def parse_organisations(xml_text: str) -> dict[str, dict]:
    """KBO number -> {name, website, email, city} for every organisation in the notice."""
    orgs = {}
    root = ET.fromstring(xml_text)
    for company in root.iter(f"{{{NS['efac']}}}Company"):
        kbo = _kbo(company.findtext("cac:PartyLegalEntity/cbc:CompanyID", namespaces=NS))
        if not kbo:
            continue
        orgs[kbo] = {
            "naam": company.findtext("cac:PartyName/cbc:Name", default="", namespaces=NS).strip(),
            "website": company.findtext("cbc:WebsiteURI", default="", namespaces=NS).strip(),
            "email": company.findtext("cac:Contact/cbc:ElectronicMail", default="", namespaces=NS).strip().lower(),
            "gemeente": company.findtext("cac:PostalAddress/cbc:CityName", default="", namespaces=NS).strip(),
            "postcode": company.findtext("cac:PostalAddress/cbc:PostalZone", default="", namespaces=NS).strip(),
        }
    return orgs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    session = requests.Session()
    notices = fetch_award_notices(session)

    wins: dict[str, list[str]] = defaultdict(list)
    for n in notices:
        ids, countries = n.get("winner-identifier") or [], n.get("winner-country") or []
        for i, raw_id in enumerate(ids):
            kbo = _kbo(raw_id)
            if kbo and (i >= len(countries) or countries[i] == "BEL"):
                wins[kbo].append(n["publication-number"])

    def fetch_xml(pub: str) -> str | None:
        try:
            r = requests.get(f"https://ted.europa.eu/en/notice/{pub}/xml", timeout=30)
            return r.text if r.ok else None
        except requests.RequestException:
            return None

    pubs = sorted({p for refs in wins.values() for p in refs})
    with ThreadPoolExecutor(max_workers=8) as pool:
        xmls = dict(zip(pubs, pool.map(fetch_xml, pubs)))

    winners = {}
    for kbo, refs in wins.items():
        info = {"naam": "", "website": "", "email": "", "gemeente": "", "postcode": ""}
        for pub in refs:
            if xmls.get(pub):
                org = parse_organisations(xmls[pub]).get(kbo)
                if org:
                    info = {k: info[k] or org[k] for k in info}
        winners[kbo] = {
            "ondernemingsnummer": kbo,
            **info,
            "email_bron": "ted" if info["email"] else "",
            "aantal_gewonnen": len(refs),
            "ted_refs": ";".join(refs),
        }

    for w in winners.values():
        w.setdefault("nace_code", "")
    kbo_enrich.enrich(winners)
    rows = list(winners.values())
    with ThreadPoolExecutor(max_workers=16) as pool:
        checked = list(pool.map(check, rows))
    # A winner's own e-mail in the notice is as trustworthy as a KBO-registered one
    for r in checked:
        if not r["send_to"] and r["email_bron"] == "ted":
            r["send_to"] = r["email"]
    checked.sort(key=lambda r: -int(r["aantal_gewonnen"]))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(checked[0].keys()))
        w.writeheader()
        w.writerows(checked)
    logger.info("Winners: %d BE companies, sendable: %d", len(checked), sum(1 for r in checked if r["send_to"]))
    logger.info("Written to %s", OUTPUT)


if __name__ == "__main__":
    main()
