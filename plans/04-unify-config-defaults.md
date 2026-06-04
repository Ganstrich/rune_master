# Plan 04: Unify Configuration Defaults

## Goal
Eliminate the confusing two-config system where `config.py` and `ProcessingConfig` have divergent defaults.

## Current State
- `config.py` defines module-level constants (e.g., `DENSITY_LEVEL_RATIO = 3`, `GROUPING_METHOD = "hybrid"`)
- `processing/config_dataclass.py` defines `ProcessingConfig` dataclass with different defaults (e.g., `equipment_density_level_ratio = 0.15`, `grouping_method = "deterministic"`)
- `main.py` builds a `ProcessingConfig` but overrides its defaults with `config.py` values, creating a hidden dependency

## Divergent Defaults

| Parameter | `config.py` | `ProcessingConfig` |
|-----------|------------|-------------------|
| `equipment_density_level_ratio` | `3` | `0.15` |
| `fallback_to_unfiltered` | `False` | `True` |
| `grouping_method` | `"hybrid"` | `"deterministic"` |
| `random_group_count` | `50` | `10` |

## Problems
- Developers changing `ProcessingConfig` defaults won't affect runtime behavior (because `config.py` overrides them)
- Developers changing `config.py` won't see the change reflected in IDE autocomplete for `ProcessingConfig`
- The `DENSITY_LEVEL_RATIO = 3` in `config.py` vs `0.15` in `ProcessingConfig` is a 20x difference — likely a bug

## Approach
1. **Choose `ProcessingConfig` as the single source of truth** for all processing-related settings
2. **Audit each constant in `config.py`** — determine if it's used anywhere other than `main.py`'s `ProcessingConfig(...)` constructor
3. **Move** any `config.py` constants that aren't API-level settings into `ProcessingConfig` with the correct defaults
4. **Keep** in `config.py` only truly API-level settings: `CACHE_FILE`, `LANGUAGE`, `GAME`, `SORT_BY`, `SORT_ORDER`, `MIN_LEVEL`, `MAX_LEVEL`, `ITEM_TYPES`, `FIELDS`
5. **Update** `main.py` to use `ProcessingConfig` defaults instead of overriding from `config.py`
6. **Remove** the `DENSITY_LEVEL_RATIO = 3` constant — it's almost certainly wrong (20x the dataclass default)

## Files Affected
- `config.py` — remove processing-related constants
- `processing/config_dataclass.py` — ensure all needed defaults are correct
- `main.py` — simplify the `ProcessingConfig(...)` constructor call

## Validation
- `grep -n "Config\." main.py` — should only reference API-level config attributes
- `python main.py --no-serve` — confirm the pipeline runs with unified defaults
- `python -c "from processing import ProcessingConfig; c = ProcessingConfig(); print(c)"` — verify defaults are sensible
