"""Samenvatting + score met Claude Sonnet — enkel voor pre-screened tenders.

Eén call per tender, structured output via tool-use zodat category/score
altijd in het verwachte formaat terugkomen (geen JSON-parsing op vrije tekst).
"""

from __future__ import annotations

import logging

from anthropic import Anthropic

from database.client import get_client

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-5"

CATEGORIES = ["Communicatie", "Marketing", "Events", "PR", "Webdesign"]

SUMMARIZE_TOOL = {
    "name": "tender_samenvatting",
    "description": "Vat een overheidsopdracht samen voor een marketing-/communicatiebureau.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": CATEGORIES,
                "description": "De categorie die het best bij deze opdracht past.",
            },
            "summary_nl": {
                "type": "string",
                "description": (
                    "Beknopte samenvatting in het Nederlands (Vlaams), 2-3 zinnen, "
                    "concreet: wat moet het bureau leveren, looptijd, bijzonderheden."
                ),
            },
            "budget_text": {
                "type": "string",
                "description": (
                    "Budget zoals het in de tekst vermeld staat (bv. '€ 85.000 – 120.000' "
                    "of '€ 60.000 / jaar'). Leeg laten als er geen budget vermeld is."
                ),
            },
            "score": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": (
                    "Relevantiescore 1-10 voor een marketing-/communicatiebureau: "
                    "hoger bij groter budget, duidelijke scope, en directe overlap "
                    "met de kernactiviteiten van zo'n bureau."
                ),
            },
        },
        "required": ["category", "summary_nl", "score"],
    },
}


def _build_prompt(title: str, authority: str | None, description: str) -> str:
    return (
        f"Titel: {title}\n"
        f"Aanbestedende overheid: {authority or 'onbekend'}\n"
        f"Omschrijving: {description or '(geen omschrijving beschikbaar)'}\n\n"
        "Vat deze overheidsopdracht samen voor een Vlaams marketing-/communicatiebureau."
    )


def summarize(client: Anthropic, title: str, authority: str | None, description: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        tools=[SUMMARIZE_TOOL],
        tool_choice={"type": "tool", "name": "tender_samenvatting"},
        messages=[{"role": "user", "content": _build_prompt(title, authority, description)}],
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Sonnet gaf geen tool_use-antwoord terug")


def extract_description(raw: dict) -> str:
    """Pak een leesbare omschrijving uit de ruwe TED-payload (meertalig veld)."""
    for field_name in ("description-proc", "description-lot"):
        value = raw.get(field_name)
        if not value:
            continue
        if isinstance(value, dict):
            for lang in ("nld", "eng", "fra"):
                if lang in value:
                    v = value[lang]
                    return v[0] if isinstance(v, list) else v
        elif isinstance(value, list) and value:
            return value[0]
    return ""


def run() -> int:
    """Verwerkt alle tenders met prescreen_relevant=true en processed_at IS NULL."""
    from datetime import datetime, timezone

    db = get_client()
    ai = Anthropic()

    result = (
        db.table("tenders")
        .select("id, title, authority, raw")
        .eq("prescreen_relevant", True)
        .is_("processed_at", "null")
        .execute()
    )
    rows = result.data or []

    done = 0
    for row in rows:
        try:
            description = extract_description(row.get("raw") or {})
            data = summarize(ai, row["title"], row.get("authority"), description)
        except Exception:
            # Eén mislukte tender mag de rest van de batch niet blokkeren;
            # processed_at blijft NULL, dus morgen opnieuw geprobeerd.
            logger.exception("Samenvatting mislukt voor %s — wordt morgen opnieuw geprobeerd", row["id"])
            continue
        db.table("tenders").update(
            {
                "category": data["category"],
                "summary": data["summary_nl"],
                "budget_text": data.get("budget_text") or None,
                "score": data["score"],
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", row["id"]).execute()
        done += 1
        logger.info("%s -> score=%s category=%s | %s", row["id"], data["score"], data["category"], row["title"][:80])

    logger.info("Samenvatting: %d/%d tenders verwerkt", done, len(rows))
    return done


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
