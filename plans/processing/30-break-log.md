# Break Observation Log

## Objective

Record what actually came out of every break, with a timestamp, so the taux
coefficient can be estimated. This is the only source of ground truth in the
system.

## Depends On

Nothing. **Start this as early as possible**, during Phase 1 if convenient.

## Why Early

The taux cannot be known before breaking and decays as an item type is broken
([../../docs/01-domain-model.md](../../docs/01-domain-model.md)). It can only be
estimated from history, so the log's value scales with how long it has been
running. Every week without it is permanently lost calibration data.

Nothing here requires capture. Manual entry is sufficient to start.

## Scope

- Add a `break_log` table:

  ```text
  break_log(
      item_id, item_level, focus, runes_received_json,
      observed_density, observed_at, source
  )
  ```

  `source` distinguishes manual entry from capture.
- `observed_density` is the total rune density received, which is directly
  comparable to the theoretical `break_density` from
  [08-break-density-and-focus.done.md](08-break-density-and-focus.done.md). Their ratio is
  the observed taux.
- Add a manual entry path: a CLI command or a small form accepting item, focus,
  and runes received.
- Store `observed_at` on every row. Observations age, because taux changes as
  the server breaks more of an item.
- No model in this plan. This is collection only.

## Acceptance Criteria

- An observation can be recorded in one command.
- `observed_at` is always populated and timezone-explicit.
- The observed-to-theoretical density ratio is computable per row.
- Rows are never overwritten; corrections are new rows.
- The log is exportable, so it survives schema changes.

## Ownership

- Primary: `data/cache_manager.py`, a new CLI entry point
- Depends on: `processing/valuation/focus.py` for the theoretical comparison

## Validation

- Round-trip a manual observation and assert the computed taux ratio.
- Confirm rows persist across runs and are not cleared by cache invalidation.

## Risks

Cache-clearing operations currently wipe tables wholesale. `break_log` is
irreplaceable observational data and must be exempt from any clear or rebuild
path. Treat it as user data, not cache.

Manual entry is error-prone, so record `source` and keep manual and captured
observations separable during analysis.
