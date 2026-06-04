# Plan 01: Fix All Type Errors

## Goal
Resolve all ~15 static analysis type errors that will cause runtime crashes or incorrect behavior.

## Files Affected
- `processing/group_mapper.py`
- `processing/community_detector.py`
- `processing/equipment_filter.py`
- `processing/tuner.py`
- `models/equipment.py`

## Errors to Fix

### `processing/group_mapper.py`
1. **L170** — `calculate_shared_resources` returns `Tuple[int, int, float]` but callers may pass `None` into `ing["total_quantity"]`. Add a guard for `None` ingredient entries.
2. **L484** — `_iter_equipment_recipe` calls `int(req.get("item_ankama_id"))` where `.get()` can return `None`. Add a `None` check before `int()` conversion.

### `processing/community_detector.py`
3. **L145** — `np.arange(resolution_range[0], ...)` — if `resolution_range` contains `None` values (from a misconfigured config), the `/` operator fails on `None`. Add validation that resolution range values are numeric.

### `processing/equipment_filter.py`
4. **L19** — `excluded_resource_ids: Optional[Set[int]] = None` but the type hint says `set`. Change default from `None` to `set()` or add a `None` guard at usage sites.

### `processing/tuner.py`
5. **L172** — `tune()` returns `Tuple[ProcessingConfig, Dict[str, Any]]` but the fallback path returns `ProcessingConfig(), {}` where `{}` is `Dict[Never, Never]`, and the success path can return `None` stats. Ensure both paths return `Dict[str, Any]`.

### `models/equipment.py`
6. **L68** — `normalize_for_matching` returns `list[str]` but the property `stat_name` is typed to return `str`. The function is used inline; ensure the return type annotation on the nested function is correct and the outer property returns `str`.

## Approach
For each file:
1. Read the current code around the flagged line
2. Add `None` guards or correct type annotations
3. Run `diagnostics` on the file after changes to confirm the error is resolved
4. Ensure no new warnings are introduced

## Validation
- Run `diagnostics` on each affected file — all type errors resolved
- Run `python -m py_compile <file>` for each file to confirm syntax validity
- Run the full pipeline with `python main.py --no-serve` to confirm no runtime regressions
