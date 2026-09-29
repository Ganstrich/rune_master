# Capture Module

The **capture** package currently provides read-only, offline-testable price
ingestion. Screen acquisition and OCR engine integration are intentionally not
implemented in this repository.

## Overview

- **price_ingestion.py** validates OCR-like rows, resolves known item names,
	rejects low-confidence prices, and writes capture/manual observations to
	`price_cache`.
- **break_ingestion.py** validates known rune types and positive quantities,
  then appends accepted break outcomes to `break_log` with `source="capture"`.
- **debug_capture.py** is retained as a historical debug script; it does not
	imply that screen automation is available.

## Usage Example

```python
from capture.price_ingestion import PriceCaptureIngestor

ingestor = PriceCaptureIngestor(cache_manager, {"Iron": 10})
ingestor.ingest_capture([{"name": "Iron", "price": 1200, "confidence": 0.98}])
```

## Extending the Module

- A future screen/OCR adapter must remain read-only and pass validated rows to
	`PriceCaptureIngestor`; it must not inject input or read process memory.

## Testing

The offline ingestion tests live in `test/test_price_ingestion.py`. Run them with:

```bash
uv run pytest -q test/test_price_ingestion.py
```

---

For more detailed documentation, see the docstrings of each module.
