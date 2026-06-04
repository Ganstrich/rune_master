# Plan 05: Remove Dead resource_optimizer.py

## Goal
Remove the unused `resource_optimizer.py` file and its associated dead config flag.

## Current State
- `processing/resource_optimizer.py` exists but is empty (or a stub)
- `ProcessingConfig.use_resource_optimizer` defaults to `True` but is never checked anywhere in the codebase
- `PROCESSING.md` lists it as "Resource optimization (placeholder)"
- No imports of `resource_optimizer` exist in any other module

## Approach
1. **Confirm no imports exist:** `grep -rn "resource_optimizer" --include="*.py"` — should only find the file itself and `PROCESSING.md`
2. **Delete** `processing/resource_optimizer.py`
3. **Remove** `use_resource_optimizer: bool = True` from `ProcessingConfig` in `config_dataclass.py`
4. **Update** `PROCESSING.md` — remove the entry from the architecture diagram and module list
5. **Update** `processing/__init__.py` — no changes needed (it's not exported)
6. **Note:** Plan 13 may re-introduce this module with actual implementation. For now, remove the dead code.

## Files Affected
- `processing/resource_optimizer.py` — delete
- `processing/config_dataclass.py` — remove `use_resource_optimizer` field
- `processing/PROCESSING.md` — remove from architecture diagram and module list

## Validation
- `grep -rn "resource_optimizer\|use_resource_optimizer" --include="*.py"` — should return zero results
- `python -c "from processing import ProcessingConfig; c = ProcessingConfig(); print(c)"` — should not show `use_resource_optimizer`
- `python main.py --no-serve` — confirm no regressions
