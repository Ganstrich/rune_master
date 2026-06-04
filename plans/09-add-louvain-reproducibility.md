# Plan 09: Add Reproducibility to Louvain Community Detection

## Goal
Make the Louvain algorithm reproducible by controlling its random seed, so the committee produces consistent results across runs.

## Current State
`CommunityDetector.find_best_louvain_partition()` calls:
```python
partition = community.best_partition(
    equipment_graph,
    resolution=resolution,
    randomize=True  # Non-deterministic!
)
```

The `randomize=True` means each run can produce a different partition for the same graph and resolution. This makes:
- The committee non-reproducible
- Debugging difficult (different results each run)
- The tuner unreliable (same config can score differently)

## Problems
- Running `python main.py` twice can produce different groups
- The tuner's grid search is noisy — a config might score well due to random luck
- Users cannot share "my grouping" and reproduce it

## Approach
1. **Add a `random_seed` parameter** to `ProcessingConfig` (already exists: `random_seed: Optional[int] = None`)
2. **Thread the seed through** `GraphGroupingExpert.discover_groups()` → `CommunityDetector.find_best_louvain_partition()` → `community.best_partition()`
3. **Use `random_state` parameter** of `community.best_partition()` instead of `randomize=True`:
   - If `random_seed` is set: `random_state=random_seed` (reproducible)
   - If `random_seed` is `None`: keep `randomize=True` (current behavior, for exploration)
4. **Also fix `find_best_bilouvain_partition`** which calls `find_best_louvain_partition` internally — the seed should propagate

### Code Changes

**`CommunityDetector.find_best_louvain_partition`:**
```python
def find_best_louvain_partition(
    equipment_graph: nx.Graph,
    equipment_resources: Dict[int, Set[int]],
    resolution_range: tuple = (1, 10, 1),
    random_seed: Optional[int] = None,
) -> Dict[int, int]:
    ...
    for resolution in np.arange(...):
        partition = community.best_partition(
            equipment_graph,
            resolution=resolution,
            random_state=random_seed,  # Replaces randomize=True
        )
    ...
```

**`GraphGroupingExpert.discover_groups`:**
```python
partition = CommunityDetector.find_best_louvain_partition(
    graph,
    resources,
    resolution_range=config.resolution_range,
    random_seed=config.random_seed,
)
```

## Files Affected
- `processing/community_detector.py` — `find_best_louvain_partition` signature and body
- `processing/experts/graph_expert.py` — pass `config.random_seed` through

## Validation
- Run `python main.py --no-serve` twice without a seed — results may differ (expected)
- Run `python main.py --no-serve` twice with `random_seed=42` — results must be identical
- Verify the tuner produces the same best config when run multiple times with a seed
