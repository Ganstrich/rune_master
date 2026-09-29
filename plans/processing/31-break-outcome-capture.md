# Break Outcome Capture

## Objective

Populate `break_log` automatically by reading the break-result screen, removing
the manual entry burden.

## Depends On

[30-break-log.md](30-break-log.md),
[21-price-capture-ingestion.done.md](21-price-capture-ingestion.done.md) for shared
pipeline components

## Scope

- Add a layout matcher and parser for the break-result screen.
- Extract the runes received, by type and quantity, plus the item broken and the
  focus used.
- Write to `break_log` with `source="capture"`.
- Reuse the screen grab, preprocessing, and OCR components from the market path;
  only layout matching and parsing are new.
- Reject low-confidence reads rather than storing them.

## Acceptance Criteria

- A break is recorded without user action.
- Rune type recognition is exact: a misidentified rune type corrupts the taux
  estimate for the wrong stat.
- Quantities are validated as positive integers.
- The parser is testable offline against stored sample images.
- Capture remains read-only: pixels from the screen, no input injection, no
  client automation, no process memory access.

## Ownership

- Primary: `capture/`
- Storage: `data/cache_manager.py`

## Validation

- Fixture images covering focused and unfocused breaks, and items with many stat
  lines.
- Cross-check captured observations against manually entered ones for the same
  breaks; agreement is the accuracy measure.

## Risks

This is independent of [21-price-capture-ingestion.done.md](21-price-capture-ingestion.done.md)
and can be built first. If market OCR proves difficult, the break-result screen
is likely the easier target and produces the more valuable data, since prices
can be entered by hand far more easily than break outcomes can be reconstructed.

Rune type confusion is the dangerous failure mode: it silently attributes yield
to the wrong stat and biases every later estimate. Prefer rejecting a read over
guessing a rune type.
