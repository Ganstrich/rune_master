# Plan 16: Add Unit Tests for Processing Logic

## Goal
Create comprehensive unit tests for each expert, the filter, and the mapper.

## Current State
`test/test_group_structure.py` exists but has 16 type errors and tests an older group format. No tests exist for:
- Graph building correctness
- Community detection quality
- Group efficiency calculation
- Filter behavior at boundary conditions
- Committee de-duplication
- Each expert's discover_groups method

## Approach
Create a new test file `test/test_processing.py` with fixtures and tests:

### Test Fixtures
```python
@pytest.fixture
def sample_equipments():
    """Create 10-15 Equipment objects with known resource overlap."""
    # Equipment 1-3: Share resources {100, 200, 300} (high overlap group)
    # Equipment 4-5: Share resources {400, 500} (small group)
    # Equipment 6: No resources (isolated)
    # Equipment 7-10: Share resources {600, 700, 800, 900} (large group)
    ...

@pytest.fixture
def sample_config():
    """Create a ProcessingConfig with known values."""
    return ProcessingConfig(
        graph_min_shared_ratio=0.2,
        group_min_size=2,
        group_max_size=10,
        group_min_shared_resources=2,
        group_efficiency_threshold=0.15,
    )
```

### Test Cases

**GraphBuilder:**
- `test_bipartite_graph_creation` — verify correct node/edge counts
- `test_jaccard_similarity` — verify edge weights match manual calculation
- `test_remove_weak_candidates` — verify isolated nodes removed

**CommunityDetector:**
- `test_louvain_partition` — verify partition covers all nodes
- `test_pairwise_similarity` — verify score for known partition
- `test_empty_graph` — verify graceful handling

**GroupMapper:**
- `test_shared_resources_calculation` — verify count for known group
- `test_efficiency_calculation` — verify ratio for known group
- `test_level_spread_filter` — verify groups with high spread are rejected (after Plan 07)
- `test_large_community_split` — verify split produces valid subgroups (after Plan 08)

**EquipmentFilter:**
- `test_density_filter` — verify filter keeps/discards correct items
- `test_fallback` — verify fallback when pool too small
- `test_zero_ratio` — verify no filtering when ratio=0

**GraphExpert:**
- `test_discover_groups_returns_valid_groups` — verify output format
- `test_groups_meet_efficiency_threshold` — verify all groups pass filter

**RandomExpert:**
- `test_reproducibility_with_seed` — same seed = same groups
- `test_no_duplicate_seeds` — verify seed uniqueness
- `test_companion_cohesion` — verify companions share resources (after Plan 10)

**GeneticExpert:**
- `test_fitness_improves_over_generations` — verify evolution works (after Plan 06)
- `test_output_groups_valid` — verify output format

**Committee:**
- `test_deduplication` — verify no duplicate groups in output
- `test_all_experts_contribute` — verify multiple experts' groups appear

## Files Affected
- `test/test_processing.py` — new file
- `test/test_group_structure.py` — fix type errors or remove if superseded

## Validation
- `pytest test/test_processing.py -v` — all tests pass
- `pytest --cov=processing test/test_processing.py` — aim for >80% coverage of processing module
- Tests should run in <30 seconds (use small fixtures, not live API data)
