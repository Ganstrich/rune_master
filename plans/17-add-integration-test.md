# Plan 17: Add Integration Test for Full Committee Pipeline

## Goal
Create an integration test that runs the full committee pipeline with known input and verifies expected output properties.

## Current State
No integration test exists. The only test file (`test/test_group_structure.py`) has 16 type errors and doesn't test the full pipeline.

## Approach
Create `test/test_integration.py` that tests the end-to-end pipeline:

### Test Strategy
Since the pipeline depends on live API data (or cached data), the integration test should:
1. **Use cached data only** — never hit the live API
2. **Create a synthetic cache** with known equipment and resource data
3. **Run the full pipeline** with a deterministic config
4. **Verify output properties** (not exact group contents, which may vary slightly)

### Test Fixtures
```python
@pytest.fixture
def synthetic_cache(tmp_path):
    """Create a cache file with known equipment and resource data."""
    cache = CacheManager(cache_file=str(tmp_path / "test_cache.db"))
    # Add 20 resources with known properties
    for i in range(1, 21):
        cache.set_resource(i, {
            "name": f"Resource {i}",
            "level": i * 10,
            "pods": i,
            "type": {"name": "Ingredient", "id": 1},
            "image_urls": {"icon": f"icon_{i}.png", "sd": f"sd_{i}.png"},
        })
    cache.save()
    return cache

@pytest.fixture
def synthetic_equipments():
    """Create 15 Equipment objects with known resource overlap."""
    # Group A (items 1-4): All share resources {1, 2, 3}
    # Group B (items 5-7): All share resources {10, 11}
    # Group C (items 8-10): All share resources {15, 16, 17}
    # Items 11-15: No resources (should be excluded)
    equipments = []
    for i in range(1, 16):
        eq = Equipment(
            ankama_id=i,
            type={"name": "ring", "id": 1},
            level=50 + i * 5,
            name=f"Test Item {i}",
            effects=[],
            stat_weight=10.0 + i,
            recipe=[],
        )
        # Assign recipes based on group membership
        if i <= 4:
            eq.recipe = [ResourceRequirement(r, 1) for r in [1, 2, 3]]
        elif i <= 7:
            eq.recipe = [ResourceRequirement(r, 1) for r in [10, 11]]
        elif i <= 10:
            eq.recipe = [ResourceRequirement(r, 1) for r in [15, 16, 17]]
        # Items 11-15 have no recipe
        equipments.append(eq)
    return equipments
```

### Test Cases

**`test_committee_pipeline_deterministic`:**
- Run committee with `random_seed=42` for reproducibility
- Verify: at least 3 groups are found (Group A, B, C)
- Verify: all groups have `sharing_efficiency >= 0.15`
- Verify: all groups have at least 2 equipment
- Verify: no duplicate groups (same equipment IDs)
- Verify: items 11-15 (no resources) are not in any group

**`test_committee_pipeline_random`:**
- Run committee with `random_seed=42`
- Verify: same output as running it again with same seed (reproducibility)
- Verify: all groups meet minimum quality thresholds

**`test_deterministic_pipeline`:**
- Run deterministic (graph) expert only
- Verify: Group A (4 items) is found as a single group
- Verify: Group B (3 items) is found as a single group
- Verify: efficiency scores are correct for known groups

**`test_filter_excludes_low_density`:**
- Run with density filtering enabled
- Verify: items with `stat_weight < level * ratio` are excluded from the pool

**`test_level_spread_filter`:**
- After Plan 07: verify groups with level spread > `max_level_spread` are rejected

### Running the Integration Test
```bash
pytest test/test_integration.py -v --timeout=60
```

## Files Affected
- `test/test_integration.py` — new file

## Validation
- All integration tests pass with synthetic data
- Tests run in <60 seconds
- Tests do not require network access (fully cached/synthetic)
- Tests verify properties, not exact output (to be resilient to minor algorithm changes)
