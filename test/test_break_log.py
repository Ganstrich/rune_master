from data.cache_manager import CacheManager
from processing.break_log import observed_taux, rune_density
from processing.valuation.density import RUNE_DENSITY


def test_break_observation_round_trips_and_is_append_only(tmp_path) -> None:
    path = str(tmp_path / "breaks.db")
    cache = CacheManager(path)
    density = rune_density({"Force": 2}, RUNE_DENSITY)
    cache.record_break_observation(1, 50, "Force", {"Force": 2}, density)
    cache.record_break_observation(1, 50, "Force", {"Force": 3}, density * 1.5)
    cache.close()

    reopened = CacheManager(path)
    rows = reopened.export_break_log()
    assert len(rows) == 2
    assert rows[0]["observed_at"].endswith("+00:00")
    assert observed_taux(rows[0]["observed_density"], density) == 1.0
    reopened.close()