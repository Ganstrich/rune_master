# Price Table Contract

## Objective

Define the price schema and the `PriceSource` interface during Phase 1, backed
by a null implementation, so that feeding real prices later is a data change
rather than a refactor.

## Depends On

[02-objective-protocol.md](02-objective-protocol.md)

## Scope

- Add `processing/valuation/prices.py`:

  ```python
  class PriceSource(Protocol):
      def resource_price(self, resource_id: int) -> float | None: ...
      def rune_price(self, stat: str) -> float | None: ...
      def depth(self, item_id: int) -> Sequence[tuple[float, int]] | None: ...
  ```

- Add `NullPriceSource` returning `None` from every method.
- Add a `price_cache` table in `data/cache_manager.py`:

  ```text
  price_cache(item_id, kind, unit_price, observed_at, source)
  ```

  where `kind` distinguishes resource, rune, and equipment, and `source` records
  whether the row came from capture or manual entry.
- Add a staleness accessor: prices older than a configurable age are reported as
  stale, not silently used.
- No objective consumes prices in this plan.

## Acceptance Criteria

- Every accessor returns `None` on a miss. Objectives must degrade to the
  price-free path rather than treat a missing price as zero, which would make an
  item appear infinitely profitable.
- Stale prices are distinguishable from missing prices.
- Swapping `NullPriceSource` for a real source requires no change outside
  construction.
- `price_cache` accepts manual rows, so prices can be entered by hand before
  capture works.

## Ownership

- Primary: new `processing/valuation/prices.py`,
  `data/cache_manager.py`
- Tests: null-source behavior, staleness boundaries

## Validation

- Assert `NullPriceSource` causes `ProfitObjective` to fall back cleanly once
  that exists.
- Test the staleness boundary at exactly the configured age.

## Risks

A stale price is worse than a missing one, because it is silently wrong and
plausible. Make staleness explicit at the interface rather than leaving callers
to check timestamps.
