"""Verzendt de digest-e-mail via Resend (REST API, geen SDK-dependency)."""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


def send(*, to: str, subject: str, html: str) -> bool:
    """Verstuurt één e-mail via Resend. Retourneert True bij succes (2xx)."""
    api_key = os.environ["RESEND_API_KEY"]
    from_email = os.environ["FROM_EMAIL"]

    resp = requests.post(
        RESEND_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"from": from_email, "to": [to], "subject": subject, "html": html},
        timeout=15,
    )

    if resp.status_code >= 300:
        logger.error("Resend-fout (%s) voor %s: %s", resp.status_code, to, resp.text)
        return False

    logger.info("Digest verzonden naar %s", to)
    return True
