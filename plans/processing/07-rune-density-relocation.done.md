# Relocate And Validate The Rune Density Table

## Objective

Recognise `STAT_WEIGHTS` as the game's rune density table, move it to the
valuation layer, and validate its values, since they feed the revenue equation
directly.

## Depends On

Nothing.

## Scope

- Move `STAT_WEIGHTS` from `processing/stat_calculator.py` to
  `processing/valuation/density.py`, renamed `RUNE_DENSITY`.
- Move the stat-name resolution helpers with it; they exist to absorb API
  singular/plural inconsistencies and belong alongside the table.
- Keep `calculate_equipment_weight` importable from its current location, or
  update `data/loaders.py`, which is its only consumer.
- Add a validation test asserting each entry matches a published density
  reference. Record the reference used in the test docstring.
- Update the description in `processing/PROCESSING.md`, which currently calls it
  "a hand-authored value model". It is a game constant.

## Acceptance Criteria

- `RUNE_DENSITY` lives in the valuation layer.
- Every entry is covered by the validation test, including the distinction
  between percentage resistances and flat resistances, which carry different
  densities.
- `data/loaders.py` continues to populate `stat_weight` unchanged.
- No behavior change to grouping.

## Ownership

- Primary: new `processing/valuation/density.py`
- Callers updated: `data/loaders.py`
- Docs: `processing/PROCESSING.md`, `docs/01-domain-model.md`

## Validation

- Compare every key against the reference table; fail on any mismatch.
- Confirm computed `stat_weight` values are unchanged for a sample of equipment.

## Risks

The table's values have never been validated line by line
([../../docs/01-domain-model.md](../../docs/01-domain-model.md)). If entries are
wrong, this plan will surface it, and downstream valuation will shift once
corrected. That is the point, but it means this plan can turn into a data
correction rather than a pure move. Split the correction into its own change if
so.
