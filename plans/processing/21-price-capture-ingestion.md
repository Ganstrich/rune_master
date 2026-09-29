# Price Capture Ingestion

## Objective

Populate `price_cache` from the game window, so rune and resource prices arrive
without manual entry.

## Depends On

[20-price-table-contract.md](20-price-table-contract.md)

## Scope

- Implement the market path of the capture pipeline: screen grab, preprocess,
  OCR, layout match, parse, write.
- Write parsed rows into `price_cache` with `source="capture"` and an accurate
  `observed_at`.
- Provide a manual entry path writing the same table with `source="manual"`, so
  prices can be corrected or supplied by hand.
- Add a confidence score per row and reject low-confidence reads rather than
  storing them.
- Note that `capture/README.md` documents eight modules of which only
  `debug_capture.py` exists. Treat capture as greenfield and update that README
  to match reality.

## Acceptance Criteria

- OCR output is validated before writing: prices are positive integers, item
  names resolve to known IDs, and unresolvable rows are logged rather than
  guessed.
- A misread never silently overwrites a good price with a bad one; prefer
  keeping the older row and flagging the conflict.
- Capture is read-only. It reads pixels from the screen and does not inject
  input, automate the client, or read process memory.
- The pipeline is testable offline against stored sample images.

## Ownership

- Primary: `capture/`
- Storage: `data/cache_manager.py`
- Docs: `capture/README.md`

## Validation

- Fixture images with known expected output, asserted end to end.
- Measure parse accuracy on a labelled sample and record it; downstream
  valuation quality is bounded by this number.

## Risks

OCR is the most fragile dependency in the system and blocks Phase 2 entirely.
This is why [20-price-table-contract.md](20-price-table-contract.md) lands first
with a null source and a manual entry path: valuation work can proceed on
hand-entered prices while capture matures.

Accuracy matters asymmetrically. An overstated rune price makes a bad group look
good and will be acted on; an understated one merely hides an opportunity.
Prefer rejecting uncertain reads.
