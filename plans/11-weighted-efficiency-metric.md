# Plan 11: Weighted Efficiency Metric

## Goal
Replace the naive `sharing_efficiency` metric with one that weights shared resources by rarity/pod-weight, so rare shared resources score higher than common ones.

## Current State
`GroupMapper.calculate_shared_resources()` computes:
```python
efficiency = shared_count / total_unique
```

Every shared resource counts as 1.0, regardless of whether it's a Level 1 herb (common, cheap) or a Level 190 rare drop (expensive, time-consuming to gather).

## Problems
- A group sharing 5 common base ores scores the same as a group sharing 5 rare endgame components
- The metric doesn't reflect actual crafting effort saved
- The tuner's quality function uses `average_efficiency`, so it can't distinguish between trivially-shared and valuably-shared groups

## Approach
1. **Add a `get_resource_weight(resource_id)` method** to `GroupMapper` that returns a weight for a resource:
   - Use the resource's `level` as a proxy for rarity (higher level = rarer)
   - Use the resource's `pod` weight as a proxy for gathering effort (higher pods = bulkier = more inventory trips)
   - Cache weights in the mapper to avoid repeated lookups
   - Default to 1.0 for unknown resources

2. **Add a `weighted_efficiency` metric** alongside the existing `efficiency`:
   ```python
   weighted_shared = sum(self.get_resource_weight(rid) for rid in shared_resources)
   weighted_total = sum(self.get_resource_weight(rid) for rid in all_resources)
   weighted_efficiency = weighted_shared / weighted_total if weighted_total > 0 else 0
   ```

3. **Add the metric to the group dict** returned by `create_group()`:
   ```python
   "weighted_efficiency": weighted_efficiency,
   "weighted_shared_count": weighted_shared,
   ```

4. **Update the tuner's quality function** to use `weighted_efficiency` instead of `average_efficiency`

5. **Keep the old `sharing_efficiency`** for backward compatibility with visualizations

## Files Affected
- `processing/group_mapper.py` — add `get_resource_weight`, update `calculate_shared_resources`, update `create_group`
- `processing/tuner.py` — update `evaluate_quality` to use `weighted_efficiency`
- `processing/random_group_builder.py` — optionally add weighted efficiency to random group metadata

## Validation
- Create a test case: two groups with the same `sharing_efficiency` but different resource rarity. Verify `weighted_efficiency` distinguishes them.
- Run the full pipeline and verify `weighted_efficiency` is populated in all groups
- Verify the tuner now prefers groups with rare shared resources
