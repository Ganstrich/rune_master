# Plan 07: Add Level-Band Awareness to GroupMapper

## Goal
Prevent grouping equipment with vastly different levels, since no crafter would craft a level 30 item alongside a level 170 item.

## Current State
`GroupMapper.map_communities()` and `map_communities_inclusive()` filter by:
- `min_group_size` / `max_group_size` (count of equipment)
- `min_shared_resources` (count of shared resources)
- `efficiency_threshold` (ratio of shared to total unique resources)

**No filter exists for level spread within a group.** A community detection algorithm can group a level 20 ring with a level 180 ring if they share enough resources.

## Problems
- Groups with extreme level ranges are useless for crafting — crafters work within level bands
- The `average_density` metric is skewed when levels vary wildly
- Visualization shows misleading groups that no player would actually craft together

## Approach
1. **Add a config parameter** to `ProcessingConfig`:
   ```python
   max_level_spread: int = 50  # Max (min_level, max_level) difference within a group
   ```
2. **Add a check in `GroupMapper.map_communities()`** (after size filtering, before shared resource calculation):
   ```python
   levels = [eq.level for eq in group_equipments]
   if max(levels) - min(levels) > self.max_level_spread:
       continue
   ```
3. **Add the same check in `map_communities_inclusive()`** and in `_process_subgroup()`
4. **Add the same check in `RandomGroupBuilder.build_random_group()`** — after finding companions, filter out companions whose level is too far from the seed's level
5. **Add the check in `GeneticGroupingExpert._calculate_individual_fitness()`** — apply a penalty for groups with high level spread

## Files Affected
- `processing/config_dataclass.py` — add `max_level_spread` field
- `processing/group_mapper.py` — add level spread check in `map_communities`, `map_communities_inclusive`, `_process_subgroup`
- `processing/random_group_builder.py` — add level filtering in `find_companions` or `build_random_group`
- `processing/experts/genetic_expert.py` — add level spread penalty in fitness function

## Validation
- Run the deterministic pipeline and verify no group has a level spread > `max_level_spread`
- Run the random pipeline and verify the same
- Check that the retention rate doesn't drop significantly (if it does, the default `max_level_spread` may be too tight)
