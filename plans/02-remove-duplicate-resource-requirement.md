# Plan 02: Remove Duplicate ResourceRequirement Definition

## Goal
Consolidate the two identical `ResourceRequirement` dataclass definitions into a single source of truth.

## Current State
- `models/recipe.py` defines `ResourceRequirement` as a frozen dataclass with `resource_id: int` and `quantity: int`
- `models/equipment.py` (L107-115) defines an identical `ResourceRequirement` frozen dataclass with the same fields
- `processing/group_mapper.py` imports from `models` (which may resolve to either)
- `processing/random_group_builder.py` does not import it directly but uses `eq.recipe` which contains instances

## Problems
- Two definitions of the same concept — if one is modified, the other drifts
- `isinstance()` checks may fail across modules if both are loaded
- Maintenance hazard: adding a field requires updating both

## Approach
1. **Keep** the definition in `models/recipe.py` (it's the dedicated recipe module)
2. **Remove** the duplicate from `models/equipment.py` (L107-115)
3. **Add** an import in `models/equipment.py`: `from models.recipe import ResourceRequirement`
4. **Update** `models/__init__.py` to export `ResourceRequirement` from `recipe.py`
5. **Search** all imports of `ResourceRequirement` across the codebase and ensure they resolve to `models.recipe`
6. **Verify** that `Equipment.recipe: List[ResourceRequirement]` still works (it should, since the class is the same)

## Files Affected
- `models/equipment.py` — remove duplicate, add import
- `models/__init__.py` — ensure export from `recipe.py`
- Any file that imports `ResourceRequirement` directly (check with `grep`)

## Validation
- Run `grep -rn "class ResourceRequirement" models/` — should appear in exactly one file
- Run `python -c "from models import ResourceRequirement; print(ResourceRequirement)"` — should succeed
- Run `python main.py --no-serve` — confirm no import errors
