# Phase 0.4: Extract Policy

## Objective

Create a single `GroupAcceptancePolicy` that every expert calls, eliminating
the triple-applied thresholds and divergent filter semantics.

## Scope

- Consolidate all acceptance thresholds into `processing/policy.py`:
  - `group_min_size` / `group_max_size`
  - `group_min_shared_resources`
  - `group_efficiency_threshold` (retire as gate — see Step 1.5)
  - `group_quality_threshold`
  - `group_max_set_share`
  - `max_line_items`
  - `max_total_units`
- Remove inline threshold checks from:
  - `processing/group_mapper.py` — delegate to policy
  - `processing/experts/genetic_expert.py` — remove three inline checks
  - `processing/experts/random_expert.py` — remove inline filter
  - `processing/random_group_builder.py` — remove inline companion filter
- The policy has one method: `accepts(group: Mapping[str, Any]) -> bool`
  and one method: `rejection_reason(group) -> str | None`.

## Acceptance Criteria

- A contract test asserts that the graph path and genetic path accept the
  identical set of candidate groups given the same config.
- `rejection_reason()` returns a string identifying the first failed threshold,
  or `None` if accepted.
- All experts call the same policy instance.
- All existing tests pass (updated where the acceptance set changes).

## Ownership

- Primary: `processing/policy.py`
- Modify: `processing/group_mapper.py`, `processing/experts/genetic_expert.py`,
  `processing/experts/random_expert.py`, `processing/random_group_builder.py`

## Validation

- Run `uv run pytest -q` — all tests pass.
- Grep for `group_min_shared_results` in expert code — no inline checks remain.
- Contract test: graph expert and genetic expert produce the same accept/reject
  decision for a set of candidate groups.

## Risks

- The genetic expert currently filters on `resource_reuse_ratio` using
  `group_efficiency_threshold`, while `GroupMapper` applies the same threshold
  to `sharing_efficiency`. These are different formulas. Consolidating them
  will change which groups are accepted. This is intentional (Failing 2) but
  must be documented in the commit message.
