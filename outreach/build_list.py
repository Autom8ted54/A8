"""Merge verified prospect sources into one outreach list.

Wave A: agencies that won Belgian marketing/communication tenders (outreach/state/ted_winners.csv)
Wave B: KBO NACE 73110 prospects with a verified address (outreach/state/prospects_verified.csv)

Filters: sendable address only, creative/communication NACE (wave A), Flanders + Brussels postcodes,
no accountant-looking addresses, deduplicated on enterprise number and e-mail.

Run: uv run python -m outreach.build_list
Output: outreach/state/outreach_list.csv (gitignored)
"""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

STATE = Path(__file__).parent / "state"
OUTPUT = STATE / "outreach_list.csv"

# Main NACE prefixes that fit "marketing- en communicatiebureau" (incl. web, video, events, design)
RELEVANT_NACE = ("73", "70", "59", "74", "58", "8230", "90", "62", "63")
# Accountant addresses (common in KBO data) and mailboxes that never reach a decision maker
ACCOUNTANT_HINTS = re.compile(
    r"acc\.|accountan|boekhoud|fiscal|comptab|fiduc|^(careers?|jobs?|hr|privacy|gdpr|dpo|noreply|no-reply|support|facturatie|invoice|billing)@",
    re.I,
)
FIELDS = ["ondernemingsnummer", "naam", "email", "gemeente", "postcode", "golf", "aantal_gewonnen", "nace_code"]


def _flanders_or_brussels(postcode: str) -> bool:
    """Wallonia: 1300–1499 and 4000–7999. Unknown postcodes are kept."""
    if not postcode.isdigit():
        return True
    pc = int(postcode)
    return not (1300 <= pc <= 1499 or 4000 <= pc <= 7999)


def _read(name: str) -> list[dict]:
    path = STATE / name
    return list(csv.DictReader(path.open(encoding="utf-8"))) if path.is_file() else []


def build() -> list[dict]:
    out, seen_kbo, seen_email = [], set(), set()

    def add(row: dict, golf: str) -> None:
        email = row["send_to"].strip().lower()
        kbo = re.sub(r"\D", "", row["ondernemingsnummer"])
        if not email or kbo in seen_kbo or email in seen_email:
            return
        if ACCOUNTANT_HINTS.search(email) or not _flanders_or_brussels(row.get("postcode", "")):
            return
        seen_kbo.add(kbo)
        seen_email.add(email)
        out.append({
            "ondernemingsnummer": kbo,
            "naam": row["naam"],
            "email": email,
            "gemeente": row.get("gemeente", ""),
            "postcode": row.get("postcode", ""),
            "golf": golf,
            "aantal_gewonnen": row.get("aantal_gewonnen", "0"),
            "nace_code": row.get("nace_code", "73110"),
        })

    for row in _read("ted_winners.csv"):
        if row.get("nace_code", "").startswith(RELEVANT_NACE):
            add(row, "A")
    for row in _read("prospects_verified.csv"):
        add(row, "B")
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    rows = build()
    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    logger.info("Outreach list: %d (wave A: %d, wave B: %d) → %s", len(rows),
                sum(r["golf"] == "A" for r in rows), sum(r["golf"] == "B" for r in rows), OUTPUT)


if __name__ == "__main__":
    main()
