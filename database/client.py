"""Supabase client factory — service role, server-side only, bypasst RLS.

Zelfde patroon als site/functions/api/waitlist.js: SUPABASE_URL +
SUPABASE_SERVICE_KEY. Nooit de anon key gebruiken vanuit deze pipeline.
"""

from __future__ import annotations

import logging
import os

from supabase import Client, create_client

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client:
    """Retourneert een gecachete Supabase-client (service role)."""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        _client = create_client(url, key)
        logger.debug("Supabase client geïnitialiseerd voor %s", url)
    return _client
