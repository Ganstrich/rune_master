# Extract Pure Building Blocks

## Objective

Create a `processing/blocks/` package of pure, stateless, config-free helpers so
that similarity and recipe arithmetic have exactly one implementation each.

## Depends On

Nothing. This is the first plan.

## Scope

- Add `blocks/similarity.py` with a single `jaccard(left, right)`.
- Replace the four existing implementations: two in `quality_metrics.py`, one in
  `orchestrator.py` (`_equipment_set_overlap`), and the inline computation in
  `graph_builder.py`.
- Add `blocks/recipes.py` for resource-set and quantity extraction, replacing the
  repeated `{req.resource_id for req in eq.recipe}` idiom and consolidating the
  `_iter_recipe` and `_iter_equipment_recipe` variants.
- Add `blocks/shopping_list.py` exposing distinct line items, total units, and
  `merge()`, built on the existing `GroupMetrics.aggregate_resources` logic.
- No behavior change. Exclusion semantics of each caller are preserved exactly.

## Acceptance Criteria

- `jaccard` is defined once; no other module computes set overlap inline.
- Resource-set extraction is defined once and handles both dataclass and dict
  recipe forms, as the current code does.
- `blocks/` imports nothing from `processing/` outside `blocks/` and `models/`.
- All existing tests pass unmodified.

## Ownership

- Primary: new `processing/blocks/`
- Callers updated: `quality_metrics.py`, `orchestrator.py`, `graph_builder.py`,
  `group_metrics.py`, `group_mapper.py`, `random_group_builder.py`
- Tests: new unit tests for each block; existing contract tests unchanged

## Validation

- Assert byte-identical group output on a fixed seed before and after.
- Unit tests for empty sets, disjoint sets, and identical sets.

## Risks

The four Jaccard call sites differ in what they operate on: `quality_metrics`
uses resource sets, `orchestrator` uses equipment-ID sets. The function is the
same but the inputs are not. Do not unify the callers, only the function.
