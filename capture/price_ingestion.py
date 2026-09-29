"""Validated OCR/manual price ingestion with no client automation."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Mapping

from data.cache_manager import CacheManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceRow:
    """A parsed market row before persistence."""

    name: str
    price: int
    confidence: float
    kind: str = "resource"


class PriceCaptureIngestor:
    """Validate and persist capture or manual price rows."""

    def __init__(
        self,
        cache_manager: CacheManager,
        known_items: Mapping[str, int],
        minimum_confidence: float = 0.9,
    ) -> None:
        self.cache_manager = cache_manager
        self.known_items = {name.casefold(): item_id for name, item_id in known_items.items()}
        self.minimum_confidence = minimum_confidence

    @staticmethod
    def parse_price(value: Any) -> int | None:
        """Parse a positive integer price, rejecting malformed OCR."""
        try:
            price = int(str(value).replace(" ", "").replace(",", ""))
        except (TypeError, ValueError):
            return None
        return price if price > 0 else None

    def parse_rows(self, rows: list[Mapping[str, Any]]) -> list[PriceRow]:
        """Validate OCR-like rows without guessing unknown item identities."""
        parsed: list[PriceRow] = []
        for row in rows:
            name = str(row.get("name", "")).strip()
            confidence = float(row.get("confidence", 0.0))
            price = self.parse_price(row.get("price"))
            if (
                not name
                or name.casefold() not in self.known_items
                or price is None
                or confidence < self.minimum_confidence
            ):
                logger.warning("Rejected price row: %s", row)
                continue
            parsed.append(PriceRow(name, price, confidence, str(row.get("kind", "resource"))))
        return parsed

    def ingest_capture(self, rows: list[Mapping[str, Any]]) -> list[PriceRow]:
        """Persist accepted rows from read-only capture with conflict protection."""
        return self._ingest(self.parse_rows(rows), "capture")

    def ingest_manual(self, rows: list[Mapping[str, Any]]) -> list[PriceRow]:
        """Persist accepted rows from manual entry using the same schema."""
        return self._ingest(self.parse_rows(rows), "manual", allow_correction=True)

    def _ingest(
        self,
        rows: list[PriceRow],
        source: str,
        allow_correction: bool = False,
    ) -> list[PriceRow]:
        accepted: list[PriceRow] = []
        now = time.time()
        for row in rows:
            item_id = self.known_items[row.name.casefold()]
            existing = self.cache_manager.get_price_status(item_id, row.kind)
            if existing and existing["unit_price"] != row.price and not allow_correction:
                logger.warning("Price conflict for %s; keeping existing value", row.name)
                continue
            self.cache_manager.set_price(item_id, row.kind, row.price, source, now)
            accepted.append(row)
        return accepted