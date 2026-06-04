# Plan 10: Add Level Spread Constraint to Groups

## Problem
Groups can contain equipment of wildly different levels (e.g., level 30 and level 190 items). While they may share resources, a player crafting level 30 items has no use for level 190 items. There's no level-range constraint on groups, reducing practical usability.

## Decision
Add a `max_level_spread` config parameter. Groups where `max(level) - min(level) > max_level_spread` are filtered out during group mapping.

## Atomic Actions

### Action 10.1: Add `max_level_spread` config parameter
- **File:** `processing/config_dataclass.py`
- **Lines:** L24-25 (after `group_efficiency_threshold`)
- **Change:** Add a new field for maximum level spread within a group.
- **Details:**
  ```python
  max_level_spread: int = 0  # Max level difference in a group (0 = no limit)
  ```

### Action 10.2: Add level spread filter in `GroupMapper.map_communities`
- **File:** `processing/group_mapper.py`
- **Lines:** L220-226 (size filter block in `map_communities`)
- **Change:** After the size filter, add a level spread check.
- **Details:**
  ```python
  # Apply level spread filter
  if config.max_level_spread > 0 and len(group_equipments) >= 2:
      levels = [eq.level for eq in group_equipments]
      if max(levels) - min(levels) > config.max_level_spread:
          continue
  ```
  - This requires `config` to be passed to `map_communities` (it currently isn't — see Action 10.3)

### Action 10.3: Pass `config` to `map_communities` in `GraphGroupingExpert`
- **File:** `processing/experts/graph_expert.py`
- **Lines:** L82-90 (calls to `mapper.map_communities` and `mapper.map_communities_inclusive`)
- **Change:** Add `config` parameter to the `map_communities` and `map_communities_inclusive` signatures and pass it through.
- **Details:**
  - Update `map_communities` signature to accept `config: Optional[ProcessingConfig] = None`
  - Update `map_communities_inclusive` signature similarly
  - Pass `config` from the expert: `mapper.map_communities(..., config=config)`
  - In the level spread check, use `config.max_level_spread if config else 0`

### Action 10.4: Add level spread filter in `GroupMapper.map_communities_inclusive`
- **File:** `processing/group_mapper.py`
- **Lines:** L354-402 (`_process_subgroup` method)
- **Change:** Add the same level spread check in the inclusive mapping path.
- **Details:** Same logic as Action 10.2, applied to subgroups before creating group dicts.
