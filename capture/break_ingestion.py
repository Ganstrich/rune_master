"""Validated break-result capture ingestion."""

import logging
from typing import Any, Mapping

from data.cache_manager import CacheManager
from processing.break_log import rune_density

logger = logging.getLogger(__name__)


class BreakOutcomeCapture:
    """Parse read-only OCR rows and append accepted break outcomes."""

    def __init__(
        self,
        cache_manager: CacheManager,
        known_items: Mapping[int, int],
        known_runes: Mapping[str, float],
        minimum_confidence: float = 0.9,
    ) -> None:
        self.cache_manager = cache_manager
        self.known_items = dict(known_items)
        self.known_runes = {name.casefold(): density for name, density in known_runes.items()}
        self.minimum_confidence = minimum_confidence

    def parse(self, row: Mapping[str, Any]) -> dict[str, Any] | None:
        """Validate one structured break-result OCR row."""
        item_id = row.get("item_id")
        try:
            item_id = int(item_id)
            item_level = int(row.get("item_level"))
            confidence = float(row.get("confidence", 0.0))
        except (TypeError, ValueError):
            return None
        runes = row.get("runes_received")
        if item_id not in self.known_items or not isinstance(runes, Mapping):
            return None
        if confidence < self.minimum_confidence:
            return None
        normalized: dict[str, int] = {}
        for name, quantity in runes.items():
            key = str(name).casefold()
            try:
                amount = int(quantity)
            except (TypeError, ValueError):
                return None
            if key not in self.known_runes or amount <= 0:
                return None
            normalized[key] = amount
        if not normalized:
            return None
        return {
            "item_id": item_id,
            "item_level": item_level,
            "focus": row.get("focus"),
            "runes_received": normalized,
            "observed_density": rune_density(normalized, self.known_runes),
        }

    def ingest(self, rows: list[Mapping[str, Any]]) -> int:
        """Append valid capture rows and return the number accepted."""
        accepted = 0
        for row in rows:
            parsed = self.parse(row)
            if parsed is None:
                logger.warning("Rejected break capture row: %s", row)
                continue
            self.cache_manager.record_break_observation(
                source="capture", **parsed
            )
            accepted += 1
        return accepted