# Plan 08: Improve Large Community Splitting

## Goal
Replace naive chunking in `_split_large_community` with resource-similarity-based splitting.

## Current State
`GroupMapper._split_large_community()` (L401-424) splits large groups by simple array slicing:

```python
for i in range(0, len(large_group), max_size):
    subgroup = large_group[i : i + max_size]
```

This ignores resource similarity entirely. Items at indices 0-7 may have nothing in common with items at indices 8-15.

## Problems
- Split subgroups can have zero shared resources, failing the `min_shared_resources` filter anyway
- Wastes computation processing subgroups that will be discarded
- Produces groups that look good by size but are useless for crafting

## Approach
Replace `_split_large_community` with a resource-overlap-based approach:

1. **Build a local similarity matrix** for items in the large group (Jaccard similarity of their resource sets)
2. **Use a greedy clustering algorithm:**
   - Pick a random seed item from the unassigned pool
   - Iteratively add the most-similar unassigned item until `max_size` is reached
   - Repeat until all items are assigned
3. **Handle leftovers:** If the last subgroup has fewer than `min_group_size` items, merge them into the most-similar existing subgroup
4. **Keep the same interface** — the method signature and return type don't change

### Pseudocode
```python
def _split_large_community(self, large_group, max_size):
    if len(large_group) <= max_size:
        return [large_group]
    
    # Build resource sets
    resource_sets = {}
    for eq in large_group:
        resource_sets[eq.ankama_id] = {r.resource_id for r in eq.recipe}
    
    unassigned = set(eq.ankama_id for eq in large_group)
    subgroups = []
    
    while unassigned:
        seed_id = unassigned.pop()
        current_group = [self.equipment_dict[seed_id]]
        current_resources = resource_sets[seed_id]
        
        while len(current_group) < max_size and unassigned:
            # Find most similar unassigned item
            best_id = None
            best_overlap = -1
            for uid in unassigned:
                overlap = len(current_resources & resource_sets[uid])
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_id = uid
            
            if best_id is None or best_overlap == 0:
                break
            
            unassigned.remove(best_id)
            current_group.append(self.equipment_dict[best_id])
            current_resources |= resource_sets[best_id]
        
        subgroups.append(current_group)
    
    return subgroups
```

## Files Affected
- `processing/group_mapper.py` — replace `_split_large_community` method (L401-424)

## Validation
- Run the deterministic pipeline with a known large community
- Verify that split subgroups have higher average shared resources than with naive chunking
- Verify no subgroup has zero shared resources (unless the input truly has none)
- Performance: the greedy approach is O(n²) per large group, which is acceptable since it only applies to oversized communities
