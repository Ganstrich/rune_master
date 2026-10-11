"""Characterization tests: lock current behavior before refactor.

These tests use a small hand-built set of Equipment objects (no network)
and store expected values as literals. They must pass against the
UNMODIFIED code and continue to pass after refactoring.
"""
import pytest

from models import Equipment, ResourceRequirement
from processing import ProcessingConfig, RuneMaster
from processing.filters.equipment_filter import EquipmentFilteringStrategy


def make_equipment(eid, recipe, set_id=None, level=50, stat_weight=100.0):
    return Equipment(
        ankama_id=eid,
        type={"id": 1, "name": "test"},
        level=level,
        name=f"Equipment {eid}",
        stat_weight=stat_weight,
        recipe=[ResourceRequirement(resource_id=r, quantity=q) for r, q in recipe],
        set_id=set_id,
    )


@pytest.fixture
def equipments():
    """10 items: two clusters of 4 with overlapping recipes, plus 2 singletons."""
    return [
        make_equipment(1, [(100, 2), (101, 1), (102, 1)]),
        make_equipment(2, [(100, 2), (101, 1), (103, 1)]),
        make_equipment(3, [(100, 2), (101, 1), (104, 1)]),
        make_equipment(4, [(100, 2), (101, 1), (105, 1)]),
        make_equipment(5, [(200, 2), (201, 1), (202, 1)]),
        make_equipment(6, [(200, 2), (201, 1), (203, 1)]),
        make_equipment(7, [(200, 2), (201, 1), (204, 1)]),
        make_equipment(8, [(200, 2), (201, 1), (205, 1)]),
        make_equipment(9, [(300, 1), (301, 1)]),
        make_equipment(10, [(301, 1), (302, 1)]),
    ]


# --- Greedy grouping ---

def test_greedy_grouping_output(equipments):
    config = ProcessingConfig(
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
    )
    master = RuneMaster(equipments, config=config)
    groups = master.run_greedy()

    assert len(groups) >= 1
    assert all(g["selection_method"] == "greedy" for g in groups)
    assert all(g["group_size"] >= 2 for g in groups)


# --- Density filtering ---

def test_density_filter_fallback_enabled(equipments):
    pool, was_filtered = EquipmentFilteringStrategy.get_active_pool(
        equipments,
        use_filtering=True,
        density_ratio=10.0,
        fallback_to_unfiltered=True,
        min_pool_size=2,
    )
    assert len(pool) == 10
    assert was_filtered is False


def test_density_filter_fallback_disabled(equipments):
    pool, was_filtered = EquipmentFilteringStrategy.get_active_pool(
        equipments,
        use_filtering=True,
        density_ratio=10.0,
        fallback_to_unfiltered=False,
        min_pool_size=2,
    )
    assert len(pool) == 0
    assert was_filtered is True


def test_density_filter_no_filtering(equipments):
    pool, was_filtered = EquipmentFilteringStrategy.get_active_pool(
        equipments,
        use_filtering=False,
        density_ratio=10.0,
        fallback_to_unfiltered=False,
        min_pool_size=2,
    )
    assert len(pool) == 10
    assert was_filtered is False


# --- get_summary() keys and value types ---

def test_get_summary_keys_and_types(equipments):
    config = ProcessingConfig(
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
    )
    master = RuneMaster(equipments, config=config)
    master.run_greedy()
    summary = master.get_summary()

    expected_keys = {
        "total_groups", "total_equipment_in_groups", "unique_equipment_in_groups",
        "total_equipment", "retention_rate", "equipment_coverage_rate",
        "duplicate_assignment_count", "assignment_overlap_rate",
        "average_efficiency", "average_quality_score",
        "assignment_weighted_quality_score", "mean_group_overlap",
        "maximum_group_overlap", "portfolio_quality_score",
        "max_efficiency", "min_efficiency", "average_group_size", "max_group_size",
    }
    assert set(summary.keys()) == expected_keys
    assert isinstance(summary["total_groups"], int)
    assert isinstance(summary["total_equipment_in_groups"], int)
    assert isinstance(summary["unique_equipment_in_groups"], int)
    assert isinstance(summary["total_equipment"], int)
    assert isinstance(summary["duplicate_assignment_count"], int)
    assert isinstance(summary["max_group_size"], int)

    for key in ["retention_rate", "equipment_coverage_rate", "assignment_overlap_rate",
                "average_efficiency", "average_quality_score",
                "assignment_weighted_quality_score", "mean_group_overlap",
                "maximum_group_overlap", "portfolio_quality_score",
                "max_efficiency", "min_efficiency", "average_group_size"]:
        assert isinstance(summary[key], float), f"{key} should be float"
