from capture.break_ingestion import BreakOutcomeCapture
from data.cache_manager import CacheManager


def test_break_capture_validates_runes_and_writes_capture_rows(tmp_path) -> None:
    cache = CacheManager(str(tmp_path / "break-capture.db"))
    capture = BreakOutcomeCapture(cache, {10: 50}, {"Force": 1.0})

    accepted = capture.ingest([
        {
            "item_id": 10,
            "item_level": 50,
            "focus": "Force",
            "runes_received": {"Force": 3},
            "confidence": 0.95,
        },
        {
            "item_id": 10,
            "item_level": 50,
            "runes_received": {"Unknown": 3},
            "confidence": 0.99,
        },
    ])

    assert accepted == 1
    rows = cache.list_break_observations()
    assert rows[0]["source"] == "capture"
    assert rows[0]["observed_density"] == 3.0
    cache.close()