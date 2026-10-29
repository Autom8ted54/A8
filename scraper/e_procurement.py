"""e-Procurement (BOSA) scraper — Belgische aanbestedingen via de FSB Media-API.

OAuth2 client credentials + zoek-API, contract geverifieerd tegen de
INT-omgeving (2026-10-29):
- Token: POST {token_url} met grant_type=client_credentials, client_id,
  client_secret (form body) -> access_token, geldig 3600 s.
- Zoeken: GET {api_base}/eProcurementSea/v1/search/publications.
  Verplicht: `page` (1-based), header `BelGov-Trace-Id` (uuid). pageSize max 100.
- Onbekende queryparameters worden stil genegeerd -> enkel geteste filters
  gebruiken: publicationDateFrom/publicationDateTo (YYYY-MM-DD).
- cpvCodes matcht enkel exacte codes (79340000 vindt geen 79341000), dus we
  halen alle recente publicaties op en filteren lokaal op CPV-prefix en
  event-zoekwoorden (events die als "logistiek" e.d. gepubliceerd worden).
- Geen deadline-veld voor alle types: oproepen tot inschrijving (eForms
  subtype 7-24, E3) hebben `vaultSubmissionDeadline`; gunningen (25-37, E4),
  wijzigingen (38-40) en vooraankondigingen (1-6) niet -> die slaan we over.
- Meertalige velden zijn lijsten van {"language": "NL", "text": ...}.

Persoonsgegevens (contactpersonen aanbesteder) worden bewust niet bewaard:
enkel organisatienaam, titel, beschrijving, CPV en datums.
"""

from __future__ import annotations

import logging
import os
import re
import time
import uuid
from datetime import date, datetime, timedelta

import requests

from database.models import RawTender
from processor.cpv_filter import is_relevant
from scraper.base import Source

logger = logging.getLogger(__name__)

SEARCH_PATH = "/eProcurementSea/v1/search/publications"
PUBLIC_URL = "https://www.publicprocurement.be/publication-workspaces/{workspace_id}/general"

PAGE_SIZE = 100  # maximum dat de API toelaat

# Ruimer dan TED: Belgische publicaties krijgen hun TED-referentie pas enkele
# dagen later, en we hebben die nodig om dubbels met TED weg te filteren.
# ~40 publicaties/dag -> 14 dagen is ±6 requests, ruim binnen de afgesproken 50/dag.
LOOKBACK_DAYS = 14

# Calls for competition (eForms 7-24) + Belgische aankondiging onder drempel (E3)
CALL_SUBTYPES = {str(n) for n in range(7, 25)} | {"E3"}

PREFERRED_LANGS = ("NL", "EN", "FR", "DE")

# Token vervalt na 3600 s; marge om niet midden in een paginering te verlopen
TOKEN_MARGIN_SECONDS = 60


def _pick_lang(values: list[dict] | None) -> str | None:
    """Kies NL, val terug op EN/FR/DE, anders eerste beschikbare tekst."""
    if not values:
        return None
    by_lang = {v.get("language"): v.get("text") for v in values if v.get("text")}
    for lang in PREFERRED_LANGS:
        if by_lang.get(lang):
            return by_lang[lang]
    return next(iter(by_lang.values()), None)


def _strip_check_digit(code: str) -> str:
    """'79340000-9' -> '79340000' (zelfde vorm als TED en de CPV-filter)."""
    return code.split("-", 1)[0]


def _parse_deadline(value: str | None) -> date | None:
    """vaultSubmissionDeadline heeft formaat '2026-12-01T10:00:00'."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        logger.warning("Kon e-Procurement-deadline niet parsen: %r", value)
        return None


def ted_number_key(ref: str) -> str | None:
    """Normaliseer een TED-publicatienummer naar 'nummer-jaar' zonder voorloopnullen.

    TED gebruikt '00123456-2026'; andere bronnen schrijven soms '123456-2026'
    of '2026/S 123-123456'. Geeft None als er geen TED-nummer in zit.
    """
    m = re.search(r"(\d{1,8})-(\d{4})\b", ref)
    if m:
        return f"{int(m.group(1))}-{m.group(2)}"
    m = re.search(r"(\d{4})/S\s*\d{1,3}-(\d{1,8})", ref)
    if m:
        return f"{int(m.group(2))}-{m.group(1)}"
    return None


class EProcurementSource(Source):
    name = "e-procurement"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        session: requests.Session | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        # API-host = host van de token-URL (public.int.fedservices.be of public.pr...)
        self.api_base = token_url.rsplit("/oauth2/", 1)[0]
        self.session = session or requests.Session()
        self._token: str | None = None
        self._token_expires_at = 0.0

    @classmethod
    def from_env(cls) -> "EProcurementSource | None":
        """Bouw de bron uit EPROC_ENV (INT|PR) + EPROC_<ENV>_*; None als niet geconfigureerd."""
        env = os.environ.get("EPROC_ENV", "").strip().upper()
        if not env:
            return None
        prefix = f"EPROC_{env}_"
        values = {k: os.environ.get(prefix + k, "").strip() for k in ("CLIENT_ID", "CLIENT_SECRET", "TOKEN_URL")}
        missing = [prefix + k for k, v in values.items() if not v]
        if missing:
            raise RuntimeError(f"e-Procurement: ontbrekende env vars {', '.join(missing)}")
        return cls(values["CLIENT_ID"], values["CLIENT_SECRET"], values["TOKEN_URL"])

    def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token
        resp = self.session.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            # Body niet loggen: kan de client_id herhalen
            raise RuntimeError(f"e-Procurement: token-aanvraag mislukt (HTTP {resp.status_code})")
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires_at = time.monotonic() + int(data.get("expires_in", 3600)) - TOKEN_MARGIN_SECONDS
        return self._token

    def _search_page(self, page: int, date_from: date) -> dict:
        resp = self.session.get(
            self.api_base + SEARCH_PATH,
            params={"page": page, "pageSize": PAGE_SIZE, "publicationDateFrom": date_from.isoformat()},
            headers={
                "Authorization": f"Bearer {self._get_token()}",
                "Accept": "application/json",
                "Accept-Language": "nl",
                "BelGov-Trace-Id": str(uuid.uuid4()),
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_publications(self) -> list[dict]:
        """Alle publicaties van de laatste LOOKBACK_DAYS, ongefilterd."""
        date_from = date.today() - timedelta(days=LOOKBACK_DAYS)
        publications: list[dict] = []
        page = 1
        while True:
            data = self._search_page(page, date_from)
            batch = data.get("publications", [])
            publications.extend(batch)
            if page * PAGE_SIZE >= data.get("totalCount", 0) or not batch:
                break
            page += 1
        return publications

    def fetch_recent(self) -> list[RawTender]:
        publications = self.fetch_publications()
        tenders = [
            self._to_raw_tender(p)
            for p in publications
            if p.get("noticeSubType") in CALL_SUBTYPES
            and is_relevant(
                self._cpv_codes(p),
                _pick_lang((p.get("dossier") or {}).get("titles")),
                _pick_lang((p.get("dossier") or {}).get("descriptions")),
            )
        ]
        logger.info(
            "e-Procurement: %d relevante oproepen uit %d publicaties (laatste %d dagen)",
            len(tenders),
            len(publications),
            LOOKBACK_DAYS,
        )
        return tenders

    @staticmethod
    def _cpv_codes(pub: dict) -> list[str]:
        main = pub.get("cpvMainCode") or {}
        codes = [main.get("code")] + [c.get("code") for c in pub.get("cpvAdditionalCodes") or []]
        return list(dict.fromkeys(_strip_check_digit(c) for c in codes if c))

    def _to_raw_tender(self, pub: dict) -> RawTender:
        dossier = pub.get("dossier") or {}
        organisation = pub.get("organisation") or {}
        workspace_id = pub.get("publicationWorkspaceId")
        return RawTender(
            source=self.name,
            source_ref=pub["referenceNumber"],
            title=_pick_lang(dossier.get("titles")) or "(geen titel)",
            authority=_pick_lang(organisation.get("organisationNames")),
            cpv_codes=self._cpv_codes(pub),
            budget_text=None,  # niet in de zoekresultaten
            deadline=_parse_deadline(pub.get("vaultSubmissionDeadline")),
            url=PUBLIC_URL.format(workspace_id=workspace_id) if workspace_id else None,
            country="BE",
            raw=pub,
        )


if __name__ == "__main__":
    from dotenv import load_dotenv

    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    source = EProcurementSource.from_env()
    if source is None:
        raise SystemExit("Zet EPROC_ENV=INT of PR")
    for t in source.fetch_recent():
        print(f"{t.source_ref} | {t.deadline} | {t.title} | {t.authority} | {t.url}")
