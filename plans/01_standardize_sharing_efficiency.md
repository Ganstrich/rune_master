# Plan 01: Standardize Sharing Efficiency Definition

## Problem
Three different definitions of "sharing_efficiency" exist across the codebase, making MoE gating network fitness scores incomparable across experts:

| File | Line | Definition |
|---|---|---|
| `group_mapper.py` | L51-64 | Resources used by **2+** equipment / total unique |
| `random_group_builder.py` | L331-354 | Resources in **ALL** equipment / total unique |
| `genetic_expert.py` | L362-366 | Resources in **ALL** equipment / total unique |

The `GroupMapper` version counts resources shared by *any 2+* items, while `RandomGroupBuilder` and `GeneticExpert` require resources to be in *every* member's recipe. The same group gets different scores depending on which expert created it.

## Decision
Standardize on the **"2+" definition** (resources used by 2+ equipment / total unique resources). This better reflects the domain goal: batch-crafting benefits from resources shared by *any* subset of items, not just universal overlap.

## Atomic Actions

### Action 1.1: Refactor `RandomGroupBuilder._calculate_efficiency` to use "2+" definition
- **File:** `processing/random_group_builder.py`
- **Lines:** L317-354 (`_calculate_efficiency` static method)
- **Change:** Replace the intersection-of-all approach with a "count resources used by 2+ equipment" approach matching `GroupMapper.calculate_shared_resources`.
- **Details:**
  - Build a `resource_usage` dict counting how many equipment use each resource
  - Count resources with usage >= 2 (excluding `self.excluded_resource_ids`)
  - Divide by total unique resources
  - Remove the now-redundant `_calculate_shared_resources` static method (L260-274) if it's only used by `_calculate_efficiency`, or update it to match

### Action 1.2: Refactor `GeneticGroupingExpert._calculate_individual_fitness` to use "2+" definition
- **File:** `processing/experts/genetic_expert.py`
- **Lines:** L317-375 (`_calculate_individual_fitness` method)
- **Change:** Replace the intersection-of-all approach with the "2+" counting approach.
- **Details:**
  - For each group (`eq_set`), count how many equipment use each resource
  - `shared_count` = number of resources used by >= 2 equipment (excluding excluded IDs)
  - `total_unique` = size of the union of all resource sets
  - `sharing_efficiency` = `shared_count / total_unique`
  - Update the docstring to reflect the new definition

### Action 1.3: Update `RandomGroupBuilder._calculate_shared_resources` to match
- **File:** `processing/random_group_builder.py`
- **Lines:** L260-274 (`_calculate_shared_resources` static method)
- **Change:** Update to count resources used by 2+ equipment (matching the "2+" definition), returning a set of resource IDs that appear in 2+ equipment recipes.
- **Note:** Check all callers of this method to ensure consistency. Currently called from `build_random_group` (L184) where the result is stored as `total_shared_resources`.

### Action 1.4: Verify `GroupMapper.calculate_shared_resources` is the canonical reference
- **File:** `processing/group_mapper.py`
- **Lines:** L31-66
- **Change:** Add a clear docstring note that this is the **canonical** definition of sharing efficiency used across all experts. No logic change needed.

### Action 1.5: Verify `evaluate_group` in base expert uses consistent metric
- **File:** `processing/experts/base.py`
- **Lines:** L43-50
- **Change:** Add a docstring note that `evaluate_group` relies on `sharing_efficiency` which follows the "2+ equipment" definition. No logic change needed.
