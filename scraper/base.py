"""Gemeenschappelijke interface voor tender-databronnen."""

from __future__ import annotations

from abc import ABC, abstractmethod

from database.models import RawTender


class Source(ABC):
    """Elke databron (TED, e-notification, ...) implementeert dit contract."""

    name: str

    @abstractmethod
    def fetch_recent(self) -> list[RawTender]:
        """Haal recent gepubliceerde, relevante tenders op als RawTender-lijst.

        Elke bron filtert zelf zo grof mogelijk (bv. CPV-codes in de query),
        de exacte CPV-controle gebeurt nadien in processor.cpv_filter.
        """
        raise NotImplementedError
