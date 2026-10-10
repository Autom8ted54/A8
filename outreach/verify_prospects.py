"""Verify prospect websites and harvest real e-mail addresses.

Belgian companies must show their enterprise number (ondernemingsnummer) on their website.
For each prospect with a website we fetch the homepage plus common contact/legal pages and:
- verified:  the KBO number appears on the site → the website really belongs to this company
- name:      the company name appears, number not found → probably right
- mismatch:  site reachable but neither found → guessed domain is likely someone else
- dead:      site unreachable
E-mail addresses found on verified/name sites are collected (same-domain preferred).

Run: uv run python -m outreach.verify_prospects
Input:  ~/Documents/kansenradar/output/kansenradar_top_prospects_verrijkt.csv
Output: outreach/state/prospects_verified.csv (gitignored: contains prospect data)
"""

from __future__ import annotations

import csv
import html
import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

logger = logging.getLogger(__name__)

INPUT = Path.home() / "Documents/kansenradar/output/kansenradar_top_prospects_verrijkt.csv"
OUTPUT = Path(__file__).parent / "state" / "prospects_verified.csv"

EXTRA_PATHS = ["contact", "contacteer-ons", "over-ons", "privacy", "privacybeleid", "disclaimer", "algemene-voorwaarden"]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LINK_RE = re.compile(r'href=["\']([^"\'#]+)["\']', re.I)
SKIP_EMAIL_PARTS = ("example", "sentry", "wixpress", "domain.", "@2x", ".png", ".jpg", ".webp", "yourname", "naam@")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/605.1.15"}
LEGAL_SUFFIXES = re.compile(r"\b(bv|bvba|nv|cv|comm\.?v|vof|vzw|sprl|sa|srl)\b\.?", re.I)


def _fetch(session: requests.Session, url: str) -> str | None:
    try:
        r = session.get(url, timeout=8, headers=HEADERS, allow_redirects=True)
        if r.status_code == 200 and "html" in r.headers.get("Content-Type", ""):
            return r.text
    except requests.RequestException:
        pass
    return None


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", LEGAL_SUFFIXES.sub("", name.lower()))


def _kbo_found(text: str, kbo: str) -> bool:
    digits = re.sub(r"\D", "", kbo)
    flat = re.sub(r"[\s.\-]", "", text)
    short = digits.lstrip("0")
    return digits in flat or (len(short) >= 9 and short in flat)


def _candidate_pages(base: str, homepage: str) -> list[str]:
    host = urlparse(base).netloc
    pages = []
    for href in LINK_RE.findall(homepage):
        url = urljoin(base, href)
        if urlparse(url).netloc == host and re.search(r"contact|privacy|disclaimer|voorwaarden|over|about|legal|colofon", url, re.I):
            pages.append(url)
    pages += [urljoin(base + "/", p) for p in EXTRA_PATHS]
    return list(dict.fromkeys(pages))[:8]


def _emails(text: str, site_domain: str) -> list[str]:
    found = []
    for e in EMAIL_RE.findall(html.unescape(text)):
        e = e.lower().strip(".")
        if any(p in e for p in SKIP_EMAIL_PARTS):
            continue
        found.append(e)
    found = list(dict.fromkeys(found))
    same = [e for e in found if e.split("@")[1].removeprefix("www.").endswith(site_domain)]
    return same or found[:2]


def _same_domain_with_mx(email: str, website: str) -> bool:
    domain = email.split("@")[-1].lower()
    site = urlparse(website if website.startswith("http") else "https://" + website).netloc.lower().removeprefix("www.")
    if domain != site:
        return False
    try:
        out = subprocess.run(["dig", "+short", "MX", domain], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return bool(out.strip())


def check(row: dict) -> dict:
    out = {**row, "site_status": "no-website", "emails_found": "", "send_to": ""}
    website = (row.get("website") or "").strip()
    if website:
        session = requests.Session()
        base = website if website.startswith("http") else "https://" + website
        homepage = _fetch(session, base)
        if homepage is None:
            out["site_status"] = "dead"
        else:
            texts = [homepage]
            if not _kbo_found(homepage, row["ondernemingsnummer"]):
                for page in _candidate_pages(base, homepage):
                    t = _fetch(session, page)
                    if t:
                        texts.append(t)
                        if _kbo_found(t, row["ondernemingsnummer"]):
                            break
            all_text = "\n".join(texts)
            if _kbo_found(all_text, row["ondernemingsnummer"]):
                out["site_status"] = "verified"
            elif len(_norm_name(row["naam"])) >= 4 and _norm_name(row["naam"]) in re.sub(r"[^a-z0-9]", "", all_text.lower()):
                out["site_status"] = "name"
            else:
                out["site_status"] = "mismatch"
            domain = urlparse(base).netloc.removeprefix("www.")
            out["emails_found"] = ";".join(_emails(all_text, domain))

    # Address choice: KBO-registered e-mail is always trusted; otherwise only from a confirmed site
    found = [e for e in out["emails_found"].split(";") if e]
    if row.get("email_bron") in ("KBO-ENT", "KBO-EST") and row.get("email"):
        out["send_to"] = row["email"]
    elif out["site_status"] in ("verified", "name"):
        if found:
            out["send_to"] = found[0]
        elif row.get("email_bron") in ("website-scrape", "duckduckgo-scrape") and row.get("email"):
            out["send_to"] = row["email"]
        elif row.get("email") and _same_domain_with_mx(row["email"], website):
            # guessed info@ on a confirmed site: only if that domain actually receives mail
            out["send_to"] = row["email"]
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    rows = list(csv.DictReader(INPUT.open(encoding="utf-8")))
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(check, rows))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    from collections import Counter

    logger.info("Site status: %s", dict(Counter(r["site_status"] for r in results)))
    logger.info("Sendable: %d of %d", sum(1 for r in results if r["send_to"]), len(results))
    logger.info("Written to %s", OUTPUT)


if __name__ == "__main__":
    main()
