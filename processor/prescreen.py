"""Pre-screening met Claude Haiku — goedkope ja/nee relevantiecheck.

Draait enkel op tenders die de CPV-filter al gehaald hebben. Voorkomt dat
elke tender de duurdere Sonnet-samenvattingsstap bereikt.
"""

from __future__ import annotations

import logging

from anthropic import Anthropic

from database.client import get_client

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"

PRESCREEN_TOOL = {
    "name": "relevantie_oordeel",
    "description": "Geef aan of deze overheidsopdracht relevant is voor een marketing- of communicatiebureau.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevant": {
                "type": "boolean",
                "description": (
                    "True als de opdracht daadwerkelijk marketing-, communicatie-, "
                    "PR-, evenementen- of webdesignwerk inhoudt dat een bureau kan "
                    "uitvoeren. False bij opdrachten die toevallig dezelfde CPV-code "
                    "hebben maar inhoudelijk iets anders zijn (bv. infrastructuurstudies, "
                    "cateringcontracten zonder communicatie-component, doorverkoop van mediaruimte)."
                ),
            }
        },
        "required": ["relevant"],
    },
}


def _build_prompt(title: str, authority: str | None, cpv_codes: list[str]) -> str:
    return (
        f"Titel: {title}\n"
        f"Aanbestedende overheid: {authority or 'onbekend'}\n"
        f"CPV-codes: {', '.join(cpv_codes)}\n\n"
        "Is dit een opdracht die een marketing- of communicatiebureau kan uitvoeren "
        "(reclame, marketing, PR, evenementen, webdesign)?"
    )


def screen(client: Anthropic, title: str, authority: str | None, cpv_codes: list[str]) -> bool:
    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        tools=[PRESCREEN_TOOL],
        tool_choice={"type": "tool", "name": "relevantie_oordeel"},
        messages=[{"role": "user", "content": _build_prompt(title, authority, cpv_codes)}],
    )
    for block in response.content:
        if block.type == "tool_use":
            return bool(block.input["relevant"])
    raise RuntimeError("Haiku gaf geen tool_use-antwoord terug")


def run() -> int:
    """Zet prescreen_relevant op alle tenders met passed_cpv=true die nog niet gescreend zijn."""
    db = get_client()
    ai = Anthropic()

    result = (
        db.table("tenders")
        .select("id, title, authority, cpv_codes")
        .eq("passed_cpv", True)
        .is_("prescreen_relevant", "null")
        .execute()
    )
    rows = result.data or []

    for row in rows:
        relevant = screen(ai, row["title"], row.get("authority"), row.get("cpv_codes") or [])
        db.table("tenders").update({"prescreen_relevant": relevant}).eq("id", row["id"]).execute()
        logger.info("%s -> relevant=%s | %s", row["id"], relevant, row["title"][:80])

    logger.info("Pre-screening: %d tenders beoordeeld", len(rows))
    return len(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
