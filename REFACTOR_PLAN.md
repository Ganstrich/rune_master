# Refactor Plan: Processing Module Improvements

## Scope

Addresses three issues from the architecture review:

1. **Duplicated metrics logic** across `GroupMapper` and `RandomGroupBuilder`
2. **Dual config system** (`config.py` + `config_dataclass.py`) with manual copying
3. **Model→processing dependency** (`EquipmentStat.stat_name` imports from `processing.stat_calculator`)

---

## Issue 1: Extract Shared `GroupMetrics` Utility

### Problem

`GroupMapper` and `RandomGroupBuilder` each independently implement:
- Shared resource calculation (intersection of recipe resources)
- Sharing efficiency (`shared_count / total_unique`)
- Resource aggregation (total quantity, per-equipment breakdown)
- Average density (`stat_weight / level`)

The formulas are duplicated with slight variations. Changing the efficiency definition means editing multiple files.

### Solution: New file `processing/group_metrics.py`

Create a single `GroupMetrics` class with **static methods** that accept a list of `Equipment` objects and return computed values. No state, no dependencies — pure functions organized in a class for namespacing.

```python
class GroupMetrics:
    """Shared metrics computation for equipment groups.

    Single source of truth for all group-level calculations.
    Used by GroupMapper, RandomGroupBuilder, GeneticGroupingExpert, and the tuner.
    """

    @staticmethod
    def shared_resources(equipments, excluded_resource_ids=None) -> set:
        """Return set of resource IDs shared by 2+ equipments (excluding excluded IDs)."""

    @staticmethod
    def shared_resources_count(equipments, excluded_resource_ids=None) -> int:
        """Count of shared resources."""

    @staticmethod
    def total_unique_resources(equipments) -> set:
        """Return set of all unique resource IDs across equipments."""

    @staticmethod
    def sharing_efficiency(equipments, excluded_resource_ids=None) -> float:
        """shared_count / total_unique (0.0 if no resources)."""

    @staticmethod
    def aggregate_resources(equipments, cache_manager=None) -> Dict[int, dict]:
        """Return {resource_id: {name, total_quantity, quantity_per_equipment}}.

        If cache_manager is provided, look up real resource names.
        """

    @staticmethod
    def average_density(equipments) -> float:
        """Average stat_weight across equipments (0.0 if empty)."""

    @staticmethod
    def build_group_dict(equipments, cache_manager=None, api_client=None,
                         excluded_resource_ids=None) -> Dict[str, Any]:
        """Build the complete group dict with all standard fields.

        This is the single factory that produces the canonical group format.
        Returns dict with keys: equipments, shared_resources_count,
        total_shared_resources (set), sharing_efficiency, average_density,
        total_ingredients, unique_ingredients_count, total_items_needed.
        """
```

### Files Changed

| File | Change |
|---|---|
| **NEW** `processing/group_metrics.py` | New shared utility class |
| `processing/group_mapper.py` | Replace inline metric calls with `GroupMetrics.*`. Keep `map_communities`, `map_communities_inclusive`, `_resolve_equipment_objects`, `_iter_equipment_recipe`, `_split_large_community` — these are mapping-specific. Replace `calculate_shared_resources`, `calculate_total_ingredients`, `calculate_average_density`, and `create_group` bodies with delegation to `GroupMetrics`. |
| `processing/random_group_builder.py` | Replace `_calculate_shared_resources`, `_aggregate_resources`, `_calculate_efficiency`, `_calculate_average_density` with delegation to `GroupMetrics`. Remove the static method duplicates entirely. |
| `processing/experts/genetic_expert.py` | Replace inline fitness resource calculation with `GroupMetrics` calls for consistency. |
| `processing/__init__.py` | Add `GroupMetrics` to exports |

### What's NOT changed

- `GroupMapper.map_communities()` and `map_communities_inclusive()` — the community→group *orchestration* logic stays; only the metric calculations are replaced with delegation.
- `RandomGroupBuilder.build_random_group()` and `build_multiple_random_groups()` — the random seed/companion selection logic stays; only metric computation is delegated.
- The group dict **schema** (field names, types) remains identical — this is a pure refactoring of where the math lives.

---

## Issue 2: Consolidate Dual Config System

### Problem

Two config objects exist:
- `config.Config` (old class in `config.py`) — holds defaults as class attributes, used by `main.py` to read CLI-overridable values
- `processing.config_dataclass.ProcessingConfig` (new dataclass) — holds the actual pipeline configuration

In `main.py::process_equipment()`, values are manually copied field-by-field from `Config` into `ProcessingConfig`. This is fragile: adding a field to one but not the other causes silent misconfiguration.

### Solution: `ProcessingConfig` as single source of truth

Make `ProcessingConfig` the **only** config object. Move the defaults currently in `config.Config` that are actually used by the processing pipeline into `ProcessingConfig`. Then have `main.py` build `ProcessingConfig` directly from CLI args + defaults, eliminating the intermediate `Config` class.

### Step-by-step

#### 2a. Merge `config.py` defaults into `ProcessingConfig`

Identify which `Config` attributes are read by `main.py` and fed into `ProcessingConfig`:

| `Config` attribute | Used as `ProcessingConfig` field | Already exists? |
|---|---|---|
| `MIN_SIMILARITY` | `graph_min_shared_ratio` | ✅ |
| `MIN_CLUSTER_SIZE` | `graph_min_component_size` / `group_min_size` | ✅ |
| `MIN_COMMON_ITEMS` | `group_min_shared_resources` | ✅ |
| `EXCLUDED_RESOURCES` | `excluded_resource_ids` | ✅ |
| `DENSITY_LEVEL_RATIO` | `equipment_density_level_ratio` | ✅ |
| `FALLBACK_TO_UNFILTERED` | `fallback_to_unfiltered` | ✅ |
| `MIN_FILTERED_POOL_SIZE` | `min_filtered_pool_size` | ✅ |
| `GROUPING_METHOD` | `grouping_method` | ✅ |
| `RANDOM_GROUP_COUNT` | `random_group_count` | ✅ |
| `MIN_EQUIPMENT_DENSITY` | (used in `loaders.py` for pre-filtering) | ❌ — add as `min_equipment_density` |
| `MIN_LEVEL` / `MAX_LEVEL` | (used in API calls) | ❌ — add as `min_level` / `max_level` if needed, or keep in a separate API config |
| `ITEM_TYPES` | (used in API calls) | ❌ — same as above |

**Decision:** Only move attributes that control *processing behavior* into `ProcessingConfig`. API-level filters (`MIN_LEVEL`, `MAX_LEVEL`, `ITEM_TYPES`, `FIELDS`, `LANGUAGE`, `GAME`, `SORT_BY`, `SORT_ORDER`) stay in `config.py` since they control data loading, not processing.

Add to `ProcessingConfig`:
```python
min_equipment_density: float = 0.0  # pre-filter in loaders
```

#### 2b. Rewrite `main.py::process_equipment()` to build `ProcessingConfig` directly

Before:
```python
config = ProcessingConfig(
    graph_min_shared_ratio=Config.MIN_SIMILARITY,
    graph_min_component_size=Config.MIN_CLUSTER_SIZE,
    ...
)
```

After:
```python
config = ProcessingConfig(
    graph_min_shared_ratio=grouping_method_or_default(Config.MIN_SIMILARITY, args.grouping_method),
    ...
)
```

Actually simpler — just read from `Config` for defaults but in one place:
```python
config = ProcessingConfig(
    graph_min_shared_ratio=Config.MIN_SIMILARITY,
    graph_min_component_size=Config.MIN_CLUSTER_SIZE,
    algorithm="louvain",
    resolution_range=(1, 10, 1),
    group_min_size=Config.MIN_CLUSTER_SIZE,
    group_max_size=18,
    group_min_shared_resources=Config.MIN_COMMON_ITEMS,
    group_efficiency_threshold=0.15,
    use_inclusive_mapping=False,
    excluded_resource_ids=set(Config.EXCLUDED_RESOURCES or []),
    use_density_filtering=True,
    equipment_density_level_ratio=density_level_ratio,
    fallback_to_unfiltered=Config.FALLBACK_TO_UNFILTERED,
    min_filtered_pool_size=Config.MIN_FILTERED_POOL_SIZE,
    grouping_method=grouping_method,
    random_group_count=random_group_count,
    random_seed=None,
    min_equipment_density=Config.MIN_EQUIPMENT_DENSITY,
)
```

This stays the same structurally — the key change is that `ProcessingConfig` now holds `min_equipment_density`, and `loaders.py` reads it from the `ProcessingConfig` instead of from `Config`.

#### 2c. Update `data/loaders.py` to accept `ProcessingConfig`

Change `EquipmentLoader.from_raw_batch()` to accept an optional `ProcessingConfig` instead of importing `Config`:
```python
def from_raw_batch(self, raw_list, processing_config=None):
    ...
    if processing_config and processing_config.min_equipment_density > 0:
        if (eq.stat_weight or 0) < processing_config.min_equipment_density:
            continue
```

#### 2d. Clean up `config.py`

Remove attributes that were moved to `ProcessingConfig`. Keep only API-level settings (`BASE_URL`, `LANGUAGE`, `GAME`, `SORT_BY`, `SORT_ORDER`, `MIN_LEVEL`, `MAX_LEVEL`, `ITEM_TYPES`, `FIELDS`, `CACHE_FILE`, `OUTPUT_PREFIX`).

Add a comment at the top:
```python
"""API-level configuration only.

Processing pipeline configuration lives in processing.config_dataclass.ProcessingConfig.
"""
```

### Files Changed

| File | Change |
|---|---|
| `processing/config_dataclass.py` | Add `min_equipment_density: float = 0.0` field |
| `main.py` | Pass `min_equipment_density` into `ProcessingConfig`. Pass `processing_config` into `loaders.from_raw_batch()` via `process_equipment()` signature. |
| `data/loaders.py` | `from_raw_batch()` accepts `processing_config` param instead of importing `Config` |
| `config.py` | Remove processing-related attributes; add docstring explaining scope |

### What's NOT changed

- `config.py` is **not deleted** — it still holds API-level settings used by `api_client.py` and the old copilot instructions.
- The CLI argument parsing in `main.py` stays the same.
- Default values don't change — they're just owned by one object instead of two.

---

## Issue 3: Break Model→Processing Dependency

### Problem

`models/equipment.py` line 41:
```python
from processing.stat_calculator import STAT_WEIGHTS
```

This creates a **circular dependency risk**: `models/` → `processing/` → (potentially) → `models/`. The model layer should be a pure data container with no knowledge of processing logic.

The `stat_name` property on `EquipmentStat` does fuzzy matching against `STAT_WEIGHTS` keys to normalize API stat names (e.g., "Dommages" → "Dommage"). This is processing/calculation concern, not a data model concern.

### Solution: Resolve stat names at calculation time, not at model access time

The `stat_name` property should return the **raw name** from the API. The fuzzy matching against `STAT_WEIGHTS` should happen in `stat_calculator.py` where the weights are actually used.

#### 3a. Simplify `EquipmentStat.stat_name` in `models/equipment.py`

Before:
```python
@property
def stat_name(self) -> str:
    from processing.stat_calculator import STAT_WEIGHTS
    raw_name = self.stat_type['name']
    # ... 30 lines of fuzzy matching ...
```

After:
```python
@property
def stat_name(self) -> str:
    """Raw stat name from the API. May need normalization for weight lookup."""
    return self.stat_type.get('name', '')
```

#### 3b. Move fuzzy matching into `processing/stat_calculator.py`

The `calculate_stat_line_weight` function already does case-insensitive matching. Add a `resolve_stat_name()` helper that does the fuzzy matching previously in the model:

```python
def resolve_stat_name(raw_name: str, stat_weights: Dict[str, float]) -> str:
    """Resolve a raw API stat name to a STAT_WEIGHTS key.

    Tries: exact match → case-insensitive → singular/plural normalization.
    Raises KeyError with helpful message if no match found.
    """
    # exact match
    if raw_name in stat_weights:
        return raw_name
    # case-insensitive
    for key in stat_weights:
        if key.lower() == raw_name.lower():
            return key
    # singular/plural normalization
    # ... (same logic as current EquipmentStat.stat_name) ...
    raise KeyError(f"Unknown stat type: '{raw_name}'. Available: {list(stat_weights.keys())}")
```

Then `calculate_stat_line_weight` calls `resolve_stat_name(stat_type, weights)` instead of doing inline matching.

#### 3c. Update `EquipmentStat.__repr__` (optional)

The `__repr__` currently uses `self.stat_name` which now returns the raw name. This is actually more useful for debugging since you see what the API actually returned.

### Files Changed

| File | Change |
|---|---|
| `models/equipment.py` | `stat_name` returns raw name. Remove the `from processing.stat_calculator import STAT_WEIGHTS` import and all fuzzy matching logic. |
| `processing/stat_calculator.py` | Add `resolve_stat_name()` function. Update `calculate_stat_line_weight()` to call it. |

### What's NOT changed

- `EquipmentStat.stat_type` (the raw dict) is unchanged.
- `calculate_equipment_weight()` signature and behavior unchanged.
- The fuzzy matching logic itself is unchanged — it just moves from the model to the calculator.
- All existing behavior is preserved; only the *location* of the resolution changes.

---

## Execution Order

These three refactors are **independent** and can be done in any order. Recommended sequence:

1. **Issue 3 first** (break dependency) — smallest blast radius, cleanest win. One import removed, one property simplified, one function added.
2. **Issue 1 second** (extract `GroupMetrics`) — most lines changed but purely mechanical delegation. Do this after Issue 3 so the genetic expert's fitness function can use the clean `GroupMetrics` from the start.
3. **Issue 2 last** (consolidate config) — touches `main.py`, `loaders.py`, and `config.py`. Do last since it changes the wiring between layers.

## Validation

After all three refactors:

- Run `python -m pytest test/test_group_structure.py` — existing tests must pass unchanged (group dict schema is identical).
- Run `python main.py --no-serve` — full pipeline must produce same output.
- Run `python main.py --grouping-method random --no-serve` — random pipeline must produce same output.
- Run `python main.py --grouping-method committee --no-serve` — committee must produce same output.
- `python -m py_compile models/equipment.py processing/group_metrics.py processing/stat_calculator.py` — no import errors.
