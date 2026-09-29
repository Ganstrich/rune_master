# Capture Module

The **capture** package provides all functionality required to capture and process game screen data for Rune Master.

## Overview

- **screen_grabber.py** – Captures screenshots from the game window.
- **preprocessor.py** – Performs image preprocessing (scaling, greyscaling, thresholding) to improve OCR accuracy.
- **ocr_engine.py** – Wraps Tesseract OCR and provides a simple `extract_text(image)` interface.
- **layout_matcher.py** – Detects UI elements and matches them against known layouts.
- **market_parser.py** – Parses market‑related information (prices, items) from the OCR output.
- **database_writer.py** – Persists parsed data into the SQLite database used by the application.
- **service.py** – High‑level service that orchestrates the capture pipeline and exposes a clean API for the rest of the project.
- **__init__.py** – Exposes the most important classes/functions for convenient imports.

## Usage Example

```python
from capture.service import CaptureService

service = CaptureService()
# Capture a frame, process it and store the result
service.run_once()
```

The `CaptureService` handles the full workflow:
1. Grab a screenshot.
2. Pre‑process the image.
3. Run OCR.
4. Match UI layout.
5. Parse market data.
6. Write results to the database.

## Extending the Module

- Add new layout matchers in **layout_matcher.py** and register them in `CaptureService`.
- Implement additional parsers in **market_parser.py** for new screen sections.
- Update **ocr_engine.py** if you switch to a different OCR backend.

## Testing

Unit tests for each component live in the `tests/capture/` directory. Run them with:

```bash
pytest tests/capture
```

---

For more detailed documentation, see the docstrings of each module.
