"""Bouwt de digest-HTML op uit een lijst tenders via het Jinja2-template."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from database.models import Tender

TEMPLATE_DIR = Path(__file__).parent / "templates"

WEEKDAGEN = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
MAANDEN = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]

CATEGORY_COLORS = {
    "Communicatie": ("#FEF3C7", "#92400E"),
    "Marketing": ("#DBEAFE", "#1E40AF"),
    "Events": ("#D1FAE5", "#065F46"),
    "PR": ("#EDE9FE", "#5B21B6"),
    "Webdesign": ("#FEE2E2", "#991B1B"),
}
DEFAULT_CATEGORY_COLOR = ("#E2E8F0", "#334155")

URGENT_DAYS = 14
SOON_DAYS = 30
DEADLINE_COLORS = {"urgent": "#EF4444", "soon": "#F5A623", "later": "#22C55E"}


def format_date_nl(d: date) -> str:
    return f"{WEEKDAGEN[d.weekday()]} {d.day} {MAANDEN[d.month - 1]} {d.year}"


def _deadline_color(deadline: date | None, today: date) -> str:
    if deadline is None:
        return DEADLINE_COLORS["later"]
    days_left = (deadline - today).days
    if days_left < URGENT_DAYS:
        return DEADLINE_COLORS["urgent"]
    if days_left < SOON_DAYS:
        return DEADLINE_COLORS["soon"]
    return DEADLINE_COLORS["later"]


def _tender_context(t: Tender, today: date) -> dict:
    bg, fg = CATEGORY_COLORS.get(t.category, DEFAULT_CATEGORY_COLOR)
    return {
        "category": t.category,
        "category_bg": bg,
        "category_fg": fg,
        "score": t.score,
        "title": t.title,
        "authority": t.authority or "",
        "summary": t.summary or "",
        "budget_text": t.budget_text,
        "deadline_str": format_date_nl(t.deadline) if t.deadline else None,
        "deadline_color": _deadline_color(t.deadline, today),
        "url": t.url or "#",
    }


def build(tenders: list[Tender], today: date, unsubscribe_url: str) -> str:
    """Rendert de digest-HTML voor een lijst tenders."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("digest.html")
    return template.render(
        date_nl=format_date_nl(today),
        tenders=[_tender_context(t, today) for t in tenders],
        unsubscribe_url=unsubscribe_url,
    )
