from capture.price_ingestion import PriceCaptureIngestor
from data.cache_manager import CacheManager


def test_capture_ingestion_rejects_bad_rows_and_preserves_conflicts(tmp_path) -> None:
    cache = CacheManager(str(tmp_path / "capture.db"))
    ingestor = PriceCaptureIngestor(cache, {"Iron": 10}, minimum_confidence=0.8)

    accepted = ingestor.ingest_capture([
        {"name": "Iron", "price": "1,200", "confidence": 0.95},
        {"name": "Unknown", "price": 2, "confidence": 0.99},
        {"name": "Iron", "price": -1, "confidence": 0.99},
    ])
    conflict = ingestor.ingest_capture([
        {"name": "Iron", "price": 1500, "confidence": 0.99}
    ])

    assert len(accepted) == 1
    assert conflict == []
    assert cache.get_current_price(10, "resource") == 1200.0
    cache.close()


def test_manual_entry_can_correct_a_capture(tmp_path) -> None:
    cache = CacheManager(str(tmp_path / "manual.db"))
    ingestor = PriceCaptureIngestor(cache, {"Iron": 10})
    ingestor.ingest_capture([{"name": "Iron", "price": 1200, "confidence": 1.0}])

    ingestor.ingest_manual([{"name": "Iron", "price": 1100, "confidence": 1.0}])

    assert cache.get_current_price(10, "resource") == 1100.0
    cache.close()