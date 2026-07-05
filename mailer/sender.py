"""Verzendt de digest-e-mail via Resend (REST API, geen SDK-dependency)."""

from __future__ import annotations

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"
RATE_LIMIT_RETRY_SECONDS = 2


def send(*, to: str, subject: str, html: str, unsubscribe_url: str | None = None) -> bool:
    """Verstuurt één e-mail via Resend. Retourneert True bij succes (2xx).

    Bij 429 (rate limit) wordt één keer opnieuw geprobeerd na een korte pauze.
    """
    api_key = os.environ["RESEND_API_KEY"]
    from_email = os.environ["FROM_EMAIL"]

    payload: dict = {"from": from_email, "to": [to], "subject": subject, "html": html}
    if unsubscribe_url:
        # Gmail/Yahoo vereisen one-click unsubscribe voor bulkverzenders
        payload["headers"] = {
            "List-Unsubscribe": f"<{unsubscribe_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }

    for attempt in (1, 2):
        try:
            resp = requests.post(
                RESEND_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15,
            )
        except requests.RequestException as exc:
            logger.error("Resend-verbindingsfout voor %s: %s", to, exc)
            return False

        if resp.status_code == 429 and attempt == 1:
            logger.warning("Resend rate limit voor %s — retry over %ds", to, RATE_LIMIT_RETRY_SECONDS)
            time.sleep(RATE_LIMIT_RETRY_SECONDS)
            continue

        if resp.status_code >= 300:
            logger.error("Resend-fout (%s) voor %s: %s", resp.status_code, to, resp.text)
            return False

        logger.info("Digest verzonden naar %s", to)
        return True

    return False
