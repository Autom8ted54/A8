"""Cold outreach sender for Kansenradar (SMTP/IMAP on the kansenradar.eu mailbox).

Sequence per agency: mail 1 (day 0), mail 2 (day 4) and mail 3 (day 10), the follow-ups as replies
in the same thread. A sequence stops as soon as the agency replies, says "stop" or bounces.
Texts come from outreach/templates.md (single source). Send volume warms up from 10 to 40 mails
per day.

Run (always from the project root):
  uv run python -m outreach.send --dry-run          show what would go out today, touch nothing
  uv run python -m outreach.send --test ADDRESS     send mail 1/2/3 of wave A and B to ADDRESS
  uv run python -m outreach.send --check            process replies, stops and bounces only
  uv run python -m outreach.send --status           counts per status
  uv run python -m outreach.send --go               real run (only after Filip's go)

Env (.env): OUTREACH_EMAIL, OUTREACH_PASSWORD, optional OUTREACH_SMTP_HOST / OUTREACH_IMAP_HOST
(default mail.<domain>), OUTREACH_FROM_NAME (default Filip), OUTREACH_REPLY_TO (default none, so
replies land in the outreach mailbox where the stop/reply detection reads them).
State: outreach/state/send_state.json (gitignored).
"""

from __future__ import annotations

import argparse
import csv
import email
import imaplib
import json
import logging
import os
import random
import re
import smtplib
import time
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

HERE = Path(__file__).parent
TEMPLATES = HERE / "templates.md"
LIST_CSV = HERE / "state" / "outreach_list.csv"
STATE_JSON = HERE / "state" / "send_state.json"

FOLLOW_UP_DAYS = {2: 4, 3: 10}  # step -> days after step 1
WARMUP_START, WARMUP_STEP, WARMUP_MAX = 10, 2, 40  # mails/day: 10, 12, 14, ... capped at 40
DELAY_SECONDS = (45, 150)  # random pause between two mails

LEGAL_SUFFIX = re.compile(r"[\s,]+(nv|bv|bvba|commv|comm\.v|vof|srl|sprl|sa|cv|cvba|vzw)\.?$", re.I)
STOP_WORDS = re.compile(r"^\s*(stop|uitschrijven|geen interesse|niet geïnteresseerd|unsubscribe)\b", re.I | re.M)
BOUNCE_SENDERS = re.compile(r"mailer-daemon|postmaster|mail delivery", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Where the quoted original starts (Gmail/Apple "> ", Outlook "Van:"/"From:" header, "Op ... schreef")
QUOTE_START = re.compile(r"^\s*(>|(van|from|verzonden|sent):\s|-{3,}\s*original|op .+ schreef|on .+ wrote)", re.I | re.M)


@dataclass(frozen=True)
class Template:
    subject: str
    body: str


# ---------- templates ----------

def load_templates(path: Path = TEMPLATES) -> dict[str, Template]:
    """Parse mails A1-A3 and B1 from templates.md; B2/B3 are A2/A3 with the b-tracking link."""
    text = path.read_text(encoding="utf-8")
    templates: dict[str, Template] = {}
    for key in ("A1", "A2", "A3", "B1"):
        m = re.search(rf"^### Mail {key}\b.*?\n(.*?)(?=^### |^---|\Z)", text, re.S | re.M)
        if not m:
            raise ValueError(f"Mail {key} not found in {path}")
        block = m.group(1).strip()
        sm = re.match(r"\*\*Onderwerp:\*\*\s*(.+)\n", block)
        if not sm:
            raise ValueError(f"Mail {key}: no **Onderwerp:** line")
        templates[key] = Template(sm.group(1).strip(), block[sm.end():].strip() + "\n")
    for step in ("2", "3"):
        templates[f"B{step}"] = Template(
            "Re: " + templates["B1"].subject,
            templates[f"A{step}"].body.replace(f"?bron=a{step}", f"?bron=b{step}"),
        )
    return templates


def clean_name(name: str) -> str:
    """'Onlyhumans NV' -> 'Onlyhumans', 'CRONOS PUBLIC SERVICES' -> 'Cronos Public Services'."""
    name = LEGAL_SUFFIX.sub("", name.strip()).strip() or name.strip()
    if name.isupper() and any(len(w) > 4 for w in name.split()):
        name = name.title()
    return name


def render(t: Template, naam: str) -> Template:
    return Template(t.subject.replace("{naam}", naam), t.body.replace("{naam}", naam))


# ---------- planning ----------

def daily_limit(first_send: date | None, today: date) -> int:
    if first_send is None:
        return WARMUP_START
    days = (today - first_send).days
    return min(WARMUP_MAX, WARMUP_START + WARMUP_STEP * max(days, 0))


def due_followups(state: dict, today: date) -> list[tuple[str, int]]:
    """(address, step) pairs whose next follow-up is due, oldest first."""
    due = []
    for addr, rec in state["prospects"].items():
        if rec["status"] != "active":
            continue
        step = len(rec["sent"]) + 1
        if step not in FOLLOW_UP_DAYS:
            continue
        first = date.fromisoformat(rec["sent"][0]["date"])
        if (today - first).days >= FOLLOW_UP_DAYS[step]:
            due.append((first, addr, step))
    return [(a, s) for _, a, s in sorted(due)]


def new_prospects(rows: list[dict], state: dict) -> list[dict]:
    """Not yet contacted, wave A before wave B, list order kept within a wave."""
    fresh = [r for r in rows if r["email"].lower() not in state["prospects"]]
    return sorted(fresh, key=lambda r: r["golf"] != "A")


def plan_today(rows: list[dict], state: dict, today: date) -> list[tuple[str, int, dict]]:
    """Follow-ups first (they keep their timing), then new prospects up to the daily limit."""
    if today.weekday() >= 5:
        return []
    first_send = date.fromisoformat(state["first_send"]) if state.get("first_send") else None
    limit = daily_limit(first_send, today) - state.get("sent_per_day", {}).get(today.isoformat(), 0)
    by_addr = {r["email"].lower(): r for r in rows}
    plan: list[tuple[str, int, dict]] = []
    for addr, step in due_followups(state, today):
        if len(plan) >= limit:
            return plan
        plan.append((addr, step, by_addr.get(addr) or state["prospects"][addr]["row"]))
    for row in new_prospects(rows, state):
        if len(plan) >= limit:
            break
        plan.append((row["email"].lower(), 1, row))
    return plan


# ---------- state ----------

def load_state(path: Path = STATE_JSON) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"first_send": None, "sent_per_day": {}, "prospects": {}}


def save_state(state: dict, path: Path = STATE_JSON) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_rows(path: Path = LIST_CSV) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("email")]


# ---------- inbox processing ----------

def classify_inbound(msg: email.message.Message, known: set[str], our_ids: dict[str, str]) -> tuple[str, str] | None:
    """Return (address, 'replied'|'stopped'|'bounced') for an inbound message, or None."""
    sender = parseaddr(msg.get("From", ""))[1].lower()
    body = _text_body(msg)
    if BOUNCE_SENDERS.search(sender) or BOUNCE_SENDERS.search(msg.get("Subject", "")):
        for found in EMAIL_RE.findall(body):
            if found.lower() in known:
                return found.lower(), "bounced"
        return None
    refs = (msg.get("In-Reply-To", "") + " " + msg.get("References", "")).split()
    addr = sender if sender in known else next((our_ids[r] for r in refs if r in our_ids), None)
    if not addr:
        return None
    reply_part = QUOTE_START.split(body, 1)[0]
    return addr, "stopped" if STOP_WORDS.search(reply_part) else "replied"


def _text_body(msg: email.message.Message) -> str:
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_type() == "text/plain":
            payload = part.get_payload(decode=True) or b""
            return payload.decode(part.get_content_charset() or "utf-8", "replace")
    return ""


def process_inbox(state: dict, cfg: dict) -> int:
    """Mark prospects that replied, said stop or bounced. Returns number of changes."""
    known = set(state["prospects"])
    our_ids = {s["message_id"]: a for a, r in state["prospects"].items() for s in r["sent"]}
    changes = 0
    with imaplib.IMAP4_SSL(cfg["imap_host"]) as imap:
        imap.login(cfg["user"], cfg["password"])
        imap.select("INBOX", readonly=True)
        since = (state.get("first_send") or date.today().isoformat())
        since_imap = datetime.fromisoformat(since).strftime("%d-%b-%Y")
        _, data = imap.search(None, "SINCE", since_imap)
        for num in data[0].split():
            _, msg_data = imap.fetch(num, "(BODY.PEEK[])")
            msg = email.message_from_bytes(msg_data[0][1])
            result = classify_inbound(msg, known, our_ids)
            if not result:
                continue
            addr, status = result
            rec = state["prospects"][addr]
            if rec["status"] == "active" or (rec["status"] == "replied" and status == "stopped"):
                rec["status"] = status
                rec["status_date"] = date.today().isoformat()
                changes += 1
                logger.info("%s -> %s", addr, status)
    return changes


# ---------- sending ----------

def build_message(cfg: dict, to: str, t: Template, step: int, thread_id: str | None) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"{cfg['from_name']} <{cfg['user']}>"
    msg["To"] = to
    msg["Subject"] = t.subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=cfg["user"].split("@")[1])
    msg["List-Unsubscribe"] = f"<mailto:{cfg['user']}?subject=stop>"
    if cfg.get("reply_to"):
        msg["Reply-To"] = cfg["reply_to"]
    if step > 1 and thread_id:
        msg["In-Reply-To"] = thread_id
        msg["References"] = thread_id
    msg.set_content(t.body)
    return msg


def send_plan(plan, templates, state, cfg, *, override_to: str | None = None, delay: bool = True) -> int:
    sent = 0
    with smtplib.SMTP_SSL(cfg["smtp_host"], 465) as smtp:
        smtp.login(cfg["user"], cfg["password"])
        for i, (addr, step, row) in enumerate(plan):
            wave = "A" if row.get("golf") == "A" else "B"
            t = render(templates[f"{wave}{step}"], clean_name(row["naam"]))
            rec = state["prospects"].get(addr)
            thread_id = rec["sent"][0]["message_id"] if rec and rec["sent"] else None
            msg = build_message(cfg, override_to or addr, t, step, thread_id)
            smtp.send_message(msg)
            sent += 1
            logger.info("Sent %s%d to %s", wave, step, override_to or addr)
            if override_to:
                continue
            today = date.today().isoformat()
            rec = state["prospects"].setdefault(addr, {"status": "active", "sent": [], "row": row})
            rec["sent"].append({"step": step, "date": today, "message_id": msg["Message-ID"]})
            state["first_send"] = state["first_send"] or today
            state["sent_per_day"][today] = state["sent_per_day"].get(today, 0) + 1
            save_state(state)  # after every mail, so a crash never causes a double send
            if delay and i < len(plan) - 1:
                time.sleep(random.uniform(*DELAY_SECONDS))
    return sent


def config() -> dict:
    load_dotenv(HERE.parent / ".env")
    user = os.environ.get("OUTREACH_EMAIL", "")
    if not user or not os.environ.get("OUTREACH_PASSWORD"):
        raise SystemExit("OUTREACH_EMAIL / OUTREACH_PASSWORD missing in .env")
    domain = user.split("@")[1]
    return {
        "user": user,
        "password": os.environ["OUTREACH_PASSWORD"],
        "smtp_host": os.environ.get("OUTREACH_SMTP_HOST", f"mail.{domain}"),
        "imap_host": os.environ.get("OUTREACH_IMAP_HOST", f"mail.{domain}"),
        "from_name": os.environ.get("OUTREACH_FROM_NAME", "Filip"),
        "reply_to": os.environ.get("OUTREACH_REPLY_TO", ""),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--test", metavar="ADDRESS")
    g.add_argument("--check", action="store_true")
    g.add_argument("--status", action="store_true")
    g.add_argument("--go", action="store_true")
    args = p.parse_args()

    templates = load_templates()
    state = load_state()

    if args.status:
        counts: dict[str, int] = {}
        for rec in state["prospects"].values():
            counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        print(f"Contacted: {len(state['prospects'])} · {counts} · first send: {state['first_send']}")
        return

    if args.dry_run:
        rows = load_rows()
        plan = plan_today(rows, state, date.today())
        print(f"Today: {len(plan)} mails")
        for addr, step, row in plan[:5]:
            wave = "A" if row.get("golf") == "A" else "B"
            t = render(templates[f"{wave}{step}"], clean_name(row["naam"]))
            print(f"\n--- {wave}{step} -> {addr}\nOnderwerp: {t.subject}\n\n{t.body}")
        if len(plan) > 5:
            print(f"... and {len(plan) - 5} more")
        return

    cfg = config()

    if args.test:
        rows = load_rows()
        sample = {w: next(r for r in rows if (r["golf"] == "A") == (w == "A")) for w in ("A", "B")}
        plan = [(r["email"].lower(), step, r) for r in sample.values() for step in (1, 2, 3)]
        scratch = {"first_send": None, "sent_per_day": {}, "prospects": {}}
        n = send_plan(plan, templates, scratch, cfg, override_to=args.test, delay=False)
        print(f"{n} test mails sent to {args.test} (state untouched)")
        return

    changes = process_inbox(state, cfg)
    save_state(state)
    print(f"Inbox processed: {changes} status changes")
    if args.check:
        return

    plan = plan_today(load_rows(), state, date.today())
    n = send_plan(plan, templates, state, cfg)
    print(f"Sent today: {n}")


if __name__ == "__main__":
    main()
