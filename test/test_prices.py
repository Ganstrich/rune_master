import time

from data.cache_manager import CacheManager
from processing.valuation.prices import CachePriceSource, NullPriceSource


def test_null_price_source_misses_every_accessor() -> None:
    source = NullPriceSource()

    assert source.resource_price(1) is None
    assert source.rune_price("Force") is None
    assert source.depth(1) is None


def test_price_cache_distinguishes_fresh_and_stale(tmp_path) -> None:
    cache = CacheManager(str(tmp_path / "prices.db"))
    cache.set_price(10, "resource", 42.0, observed_at=time.time() - 9)

    assert cache.get_current_price(10, "resource", max_age_seconds=10) == 42.0
    assert cache.get_current_price(10, "resource", max_age_seconds=5) is None
    assert cache.get_price_status(10, "resource", max_age_seconds=5)["stale"] is True
    assert CachePriceSource(cache, 5).resource_price(10) is None
    cache.close()