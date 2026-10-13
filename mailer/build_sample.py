"""Builds the sample digest sent in the waitlist thank-you mail.

Reads curated real tenders from mailer/sample_tenders.json, renders them with the regular
digest template and adapts header/footer for a waitlist signup.

Run: uv run python -m mailer.build_sample
Output: site/api/sample-digest.html (sent by site/api/waitlist.php)
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from database.models import Tender
from mailer import digest_builder

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_JSON = Path(__file__).parent / "sample_tenders.json"
OUTPUT = ROOT / "site" / "api" / "sample-digest.html"

UNSUBSCRIBE = "mailto:hallo@kansenradar.be?subject=Uitschrijven%20wachtlijst"

INTRO = """
          <!-- Waitlist intro -->
          <tr>
            <td style="background-color:#ffffff;padding:28px 32px 4px;border-bottom:1px solid #E2E8F0;">
              <p style="margin:0 0 12px;font-size:15px;font-weight:600;color:#0E2340;">Bedankt, je staat op de founding member-lijst.</p>
              <p style="margin:0 0 12px;font-size:14px;color:#374151;line-height:1.6;">Hieronder zie je hoe je Kansenradar eruit zal zien. Geen verzonnen voorbeeld: dit zijn vijf echte opdrachten voor marketing- en communicatiebureaus, gepubliceerd in de voorbije weken. Sommige deadlines zijn misschien al voorbij. Straks krijg je ze elke maandag, gebundeld per week.</p>
              <p style="margin:0 0 24px;font-size:14px;color:#374151;line-height:1.6;">Zodra we lanceren, nemen we persoonlijk contact op. Vragen of feedback? Antwoord gewoon op deze mail.<br>Filip, Kansenradar</p>
            </td>
          </tr>
"""

REPLACEMENTS = [
    # (old, new) — each must occur exactly once in the rendered template
    ("<!-- Body -->", INTRO.strip() + "\n\n          <!-- Body -->"),
    ("Je ontvangt deze digest als founding member van Kansenradar.",
     "Je ontvangt deze mail omdat je je inschreef op de wachtlijst van Kansenradar."),
    ("Bronnen: e-Procurement BE &amp; TED EU",
     "Bron van deze voorbeelden: TED EU"),
]


def load_tenders() -> list[Tender]:
    rows = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    return [
        Tender.from_row({**row, "id": row["source_ref"], "source": "ted", "cpv_codes": [], "country": "BE"})
        for row in rows
    ]


def build_sample(today: date) -> str:
    html = digest_builder.build(load_tenders(), today, UNSUBSCRIBE)
    # Greeting line in the header: replace the per-day phrasing with a sample phrasing
    greeting_start = html.index("Goedemorgen — ")
    greeting_end = html.index("</p>", greeting_start)
    html = html[:greeting_start] + "Een voorbeeld van je wekelijkse digest, met echte opdrachten." + html[greeting_end:]
    for old, new in REPLACEMENTS:
        if html.count(old) != 1:
            raise ValueError(f"Template changed: expected exactly one occurrence of {old!r}")
        html = html.replace(old, new)
    return html


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    OUTPUT.write_text(build_sample(date.today()), encoding="utf-8")
    logger.info("Sample digest written to %s", OUTPUT)


if __name__ == "__main__":
    main()
