# Plan 07: Optimize Random Group Builder Companion Scan

## Problem
`RandomGroupBuilder.find_companions()` scans the **entire equipment pool** for each seed, computing set intersections with every candidate. With `random_group_count=50` and a pool of thousands, this is O(50 × n). The companion-finding logic is the bottleneck for the random expert.

## Decision
Build an inverted index (`resource_id → [equipment_ids]`) once, then for a seed, only examine equipment that shares at least one resource with it.

## Atomic Actions

### Action 7.1: Add `_build_resource_index` method to `RandomGroupBuilder`
- **File:** `processing/random_group_builder.py`
- **Lines:** After L46 (after `__init__`, before `select_random_seed`)
- **Change:** Add a method that builds a resource→equipment inverted index from the equipment pool.
- **Details:**
  ```python
  def _build_resource_index(
      self, equipment_pool: List[Equipment]
  ) -> Dict[int, List[int]]:
      """Build inverted index: resource_id -> list of equipment IDs in pool."""
      index: Dict[int, List[int]] = {}
      pool_ids = {e.ankama_id for e in equipment_pool}
      for eq in equipment_pool:
          for req in eq.recipe:
              rid = req.resource_id
              if rid not in index:
                  index[rid] = []
              index[rid].append(eq.ankama_id)
      return index
  ```

### Action 7.2: Refactor `find_companions` to use inverted index
- **File:** `processing/random_group_builder.py`
- **Lines:** L78-138 (`find_companions` method)
- **Change:** Use the inverted index to find candidate companions instead of scanning the full pool.
- **Details:**
  1. Build the inverted index from `equipment_pool` (or accept it as a parameter)
  2. For the seed's resources, collect all equipment IDs from the index
  3. Filter to only candidates in the pool that aren't the seed itself
  4. Count shared resources only for these candidates
  5. Apply the existing `min_shared_resources` threshold and sorting

### Action 7.3: Cache the index in `build_multiple_random_groups`
- **File:** `processing/random_group_builder.py`
- **Lines:** L206-258 (`build_multiple_random_groups` method)
- **Change:** Build the inverted index once and pass it to `find_companions` for each iteration.
- **Details:**
  - Build index before the loop at L229
  - Pass it to `build_random_group` → `find_companions` (requires adding parameter to `build_random_group` as well)
