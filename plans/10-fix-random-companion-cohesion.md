# Plan 10: Fix Companion Cohesion in Random Expert

## Goal
Ensure that companions in a random group share resources with *each other*, not just with the seed equipment.

## Current State
`RandomGroupBuilder.find_companions()` finds equipment that shares resources with the seed, but doesn't check whether companions share resources with each other.

Example of the problem:
- Seed: Equipment A (resources: {1, 2, 3, 4, 5})
- Companion B shares {1, 2} with A
- Companion C shares {3, 4} with A
- B and C share nothing with each other

The group {A, B, C} has `shared_resources = {1, 2, 3, 4}` (4 items), but no single resource is shared by all three. For crafting, this is nearly useless — you can't batch-craft anything.

## Problems
- Groups look good by `shared_resources_count` but have no common crafting path
- The `sharing_efficiency` metric (shared / total unique) masks this because it only checks pairwise-with-seed sharing
- Crafters get groups where they must gather completely different ingredient subsets for each item

## Approach
Add a **cohesion check** after finding companions:

1. **After finding companions**, compute the set of resources shared by ALL group members (seed + companions)
2. **Filter companions** to ensure the final group has at least `min_shared_resources` that are common to ALL members (not just seed-to-companion)
3. **Optionally, add a cohesion score** to the group metadata:
   ```python
   cohesion = len(resources_shared_by_all) / len(resources_shared_by_seed)
   ```
   A cohesion of 1.0 means every resource shared with the seed is also shared by all companions.

### Implementation in `build_random_group`:
```python
# After finding companions and before building the group:
group_equipments = [seed_equipments] + companions

# Compute resources shared by ALL members
all_shared = self._calculate_shared_resources(group_equipments)
if len(all_shared) < min_shared_resources:
    # Try removing the worst companion (lowest overlap with seed)
    # and re-check, iteratively
    while companions and len(all_shared) < min_shared_resources:
        companions.pop()  # Remove last (lowest similarity) companion
        group_equipments = [seed_equipment] + companions
        all_shared = self._calculate_shared_resources(group_equipments)
```

## Files Affected
- `processing/random_group_builder.py` — `build_random_group` method (L140-204)

## Validation
- Run the random pipeline and verify that every group has `shared_resources` that are present in ALL members
- Compare the average `sharing_efficiency` before and after — it should be lower (stricter) but more meaningful
- Verify that no group has companions that are completely disjoint from each other
