# Phase 0.2: Extract Shopping List Blocks

## Objective

Create a `ShoppingList` value object that encapsulates line items, units,
and merge operations, making the shopping list a first-class scored entity.

## Scope

- Create `processing/blocks/shopping_list.py` with a `ShoppingList` dataclass.
- The object should expose:
  - `line_item_count: int` — number of distinct resources
  - `total_units: int` — total quantity across all resources
  - `compression: float` — 1 - |union| / sum(|individual|)
  - `merge(other: ShoppingList) -> ShoppingList` — combine two lists
- Extract the aggregation logic currently in `GroupMetrics.aggregate_resources()`.
- Update `visualization/html_generator.py` to use `ShoppingList` instead of
  re-deriving totals from `total_ingredients` dicts.

## Acceptance Criteria

- `ShoppingList` can be constructed from a list of `Equipment` objects.
- `ShoppingList.line_item_count` matches the current `unique_ingredients_count`.
- `ShoppingList.total_units` matches the current `total_items_needed`.
- `ShoppingList.merge(other)` produces a list whose `line_item_count` is the
  union of both lists' resources.
- The combined shopping list feature (plan 04) uses `ShoppingList.merge()`.

## Ownership

- Primary: `processing/blocks/shopping_list.py` (new)
- Modify: `processing/group_metrics.py`, `visualization/html_generator.py`

## Validation

- Unit test: construct two `ShoppingList` objects, merge, verify counts.
- Integration test: generate a report, verify the combined list totals match.
- Run `uv run pytest -q` — all tests pass.

## Risks

- The `ShoppingList` must handle missing resource names gracefully (the
  current code uses `f"Resource {id}"` as a fallback).
- `merge()` must deduplicate resources correctly (sum quantities, not append).
