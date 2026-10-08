"""Price-source contracts and cache-backed price access."""

from collections.abc import Sequence
from typing import Protocol


class PriceSource(Protocol):
    """Read current resource, rune, and market-depth prices."""

    def resource_price(self, resource_id: int) -> float | None: ...

    def rune_price(self, stat: str) -> float | None: ...

    def depth(self, item_id: int) -> Sequence[tuple[float, int]] | None: ...


class NullPriceSource:
    """Price source used before market data is available."""

    def resource_price(self, resource_id: int) -> None:
        del resource_id
        return None

    def rune_price(self, stat: str) -> None:
        del stat
        return None

    def depth(self, item_id: int) -> None:
        del item_id
        return None


class CachePriceSource:
    """Price source backed by CacheManager with explicit staleness policy."""

    def __init__(self, cache_manager: object, max_age_seconds: float) -> None:
        self.cache_manager = cache_manager
        self.max_age_seconds = max_age_seconds

    def resource_price(self, resource_id: int) -> float | None:
        return self.cache_manager.get_current_price(resource_id, "resource", self.max_age_seconds)

    def rune_price(self, stat: str) -> float | None:
        return self.cache_manager.get_current_price(hash(stat), "rune", self.max_age_seconds)

    def depth(self, item_id: int) -> Sequence[tuple[float, int]] | None:
        del item_id
        return None