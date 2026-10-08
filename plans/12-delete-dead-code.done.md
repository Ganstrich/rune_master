# Phase 0.5: Delete Dead Code

## Objective

Remove dead and wrong code that accumulates surface area and confusion.

## Scope

- Delete `processing/resource_optimizer.py` — empty file, no consumers.
- Remove `use_resource_optimizer` from `processing/config_dataclass.py` —
  read by nothing.
- Remove `calculate_bulk_efficiency` from `processing/community_detector.py` —
  dead and wrong (uses `set.intersection(*all)` where the spec says "used by >= 2").
- Remove `api_client` parameter threading through `group_metrics.py` and
  callers — it is `del`'d on arrival and never used.
- Remove unused imports that result from the above deletions.

## Acceptance Criteria

- `python3 -m compileall -q processing` — no errors.
- `grep -rn "resource_optimizer\|use_resource_optimizer\|calculate_bulk_efficiency" processing/`
  — no matches.
- `grep -rn "api_client" processing/group_metrics.py` — no matches.
- All existing tests pass.

## Ownership

- Delete: `processing/resource_optimizer.py`
- Modify: `processing/config_dataclass.py`, `processing/community_detector.py`,
  `processing/group_metrics.py`

## Validation

- Run `uv run pytest -q` — all tests pass.
- Run `grep -rn "resource_optimizer\|use_resource_optimizer\|calculate_bulk_efficiency" .`
  — no matches outside of `docs/` and `plans/`.

## Risks

- Verify no dynamic imports or `__all__` references exist before deleting.
