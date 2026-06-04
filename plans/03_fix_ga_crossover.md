# Plan 03: Fix Genetic Algorithm Crossover

## Problem
The `_crossover` method in `GeneticGroupingExpert` only exchanges equipment IDs that exist in **both** parents (`common_ids = p1_ids & p2_ids`). Since each individual is a partition of different equipment subsets, parents typically have **zero** overlapping IDs. When `common_ids` is empty, the method returns the parents unchanged (line 408), making crossover a no-op. The GA relies almost entirely on mutation.

## Decision
Replace the ID-based crossover with a **group-based crossover**: randomly assign each parent's groups to children, then resolve conflicts (same equipment in multiple child groups) by keeping the assignment that yields higher local sharing efficiency.

## Atomic Actions

### Action 3.1: Replace `_crossover` method with group-based crossover
- **File:** `processing/experts/genetic_expert.py`
- **Lines:** L387-457 (`_crossover` method)
- **Change:** Rewrite the entire method.
- **Details of new algorithm:**
  1. Collect all groups from both parents into a pool
  2. For each group in the pool, randomly assign it to child1, child2, or both
  3. After assignment, check for equipment appearing in multiple groups within the same child
  4. For conflicts, keep the equipment in the group where it has more shared resources with other members (higher local efficiency contribution), and remove it from the other group
  5. Remove any groups that fall below `config.group_min_size` after conflict resolution
  6. Return the two children

### Action 3.2: Add helper method to compute equipment's contribution to group efficiency
- **File:** `processing/experts/genetic_expert.py`
- **Lines:** After L375 (after `_calculate_individual_fitness`)
- **Change:** Add a new static helper method `_equipment_group_affinity`.
- **Details:**
  ```python
  @staticmethod
  def _equipment_group_affinity(eq_id: int, group_ids: Set[int],
                                 resource_sets: Dict[int, Set[int]]) -> float:
      """Measure how well an equipment fits in a group by resource overlap."""
      eq_resources = resource_sets.get(eq_id, set())
      if not eq_resources or not group_ids:
          return 0.0
      group_resources: Set[int] = set()
      for gid in group_ids:
          group_resources |= resource_sets.get(gid, set())
      if not group_resources:
          return 0.0
      return len(eq_resources & group_resources) / len(eq_resources | group_resources)
  ```
  - Used during conflict resolution in the new crossover

### Action 3.3: Add `resource_sets` parameter to `_crossover`
- **File:** `processing/experts/genetic_expert.py`
- **Lines:** L387 (method signature)
- **Change:** Add `resource_sets: Dict[int, Set[int]]` parameter to `_crossover`.
- **Details:** The crossover needs resource sets to resolve conflicts. Update the call site at L117-118 to pass `resource_sets`.

### Action 3.4: Update the call site in `discover_groups`
- **File:** `processing/experts/genetic_expert.py`
- **Lines:** L114-118 (crossover call in evolution loop)
- **Change:** Pass `resource_sets` to `_crossover`.
- **Details:** Change `self._crossover(parent1, parent2)` to `self._crossover(parent1, parent2, resource_sets)`.
