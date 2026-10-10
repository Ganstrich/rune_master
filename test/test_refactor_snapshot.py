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


# --- Deterministic grouping ---

def test_deterministic_grouping_output(equipments):
    config = ProcessingConfig(
        algorithm="none",
        graph_min_shared_ratio=0.0,
        graph_min_shared_count=1,
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
    )
    master = RuneMaster(equipments, config=config)
    groups = master.run_deterministic()

    assert len(groups) == 3

    ids_0 = sorted(e.ankama_id for e in groups[0]["equipments"])
    ids_1 = sorted(e.ankama_id for e in groups[1]["equipments"])
    ids_2 = sorted(e.ankama_id for e in groups[2]["equipments"])
    assert ids_0 == [1, 2, 3, 4]
    assert ids_1 == [5, 6, 7, 8]
    assert ids_2 == [9, 10]

    assert groups[0]["group_size"] == 4
    assert groups[0]["shared_resources_count"] == 2
    assert groups[0]["sharing_efficiency"] == pytest.approx(0.333333, abs=1e-6)
    assert groups[0]["quality_score"] == pytest.approx(0.65, abs=1e-6)

    assert groups[1]["group_size"] == 4
    assert groups[1]["shared_resources_count"] == 2
    assert groups[1]["sharing_efficiency"] == pytest.approx(0.333333, abs=1e-6)
    assert groups[1]["quality_score"] == pytest.approx(0.65, abs=1e-6)

    assert groups[2]["group_size"] == 2
    assert groups[2]["shared_resources_count"] == 1
    assert groups[2]["sharing_efficiency"] == pytest.approx(0.333333, abs=1e-6)
    assert groups[2]["quality_score"] == pytest.approx(0.45, abs=1e-6)


# --- Random grouping with fixed seed ---

def test_random_grouping_with_fixed_seed(equipments):
    config = ProcessingConfig(
        random_seed=42,
        random_group_count=5,
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
        use_density_filtering=False,
    )
    master = RuneMaster(equipments, config=config)
    groups = master.run_random_grouping()

    assert len(groups) == 5

    seeds = [g["seed_equipment_id"] for g in groups]
    assert seeds == [2, 1, 7, 4, 5]

    ids_0 = sorted(e.ankama_id for e in groups[0]["equipments"])
    ids_2 = sorted(e.ankama_id for e in groups[2]["equipments"])
    assert ids_0 == [1, 2, 3, 4]
    assert ids_2 == [5, 6, 7, 8]


# --- Hybrid supplementation ---

def test_hybrid_supplements_small_deterministic_result(equipments):
    config = ProcessingConfig(
        algorithm="none",
        graph_min_shared_ratio=0.0,
        graph_min_shared_count=1,
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
        random_group_count=3,
        random_seed=42,
        use_density_filtering=False,
    )
    master = RuneMaster(equipments, config=config)
    groups = master.run_hybrid_grouping()

    # 3 deterministic + 3 random supplement
    assert len(groups) == 6


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
        algorithm="none",
        graph_min_shared_ratio=0.0,
        graph_min_shared_count=1,
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
    )
    master = RuneMaster(equipments, config=config)
    master.run_deterministic()
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

    assert summary["total_groups"] == 3
    assert summary["total_equipment"] == 10
    assert summary["total_equipment_in_groups"] == 10
    assert summary["unique_equipment_in_groups"] == 10
    assert summary["retention_rate"] == pytest.approx(1.0)
    assert summary["equipment_coverage_rate"] == pytest.approx(1.0)
    assert summary["duplicate_assignment_count"] == 0
    assert summary["assignment_overlap_rate"] == pytest.approx(0.0)
    assert summary["average_efficiency"] == pytest.approx(0.333333, abs=1e-6)
    assert summary["average_quality_score"] == pytest.approx(0.583333, abs=1e-6)
    assert summary["assignment_weighted_quality_score"] == pytest.approx(0.61, abs=1e-6)
    assert summary["mean_group_overlap"] == pytest.approx(0.0)
    assert summary["maximum_group_overlap"] == pytest.approx(0.0)
    assert summary["portfolio_quality_score"] == pytest.approx(0.7465, abs=1e-6)
    assert summary["max_efficiency"] == pytest.approx(0.333333, abs=1e-6)
    assert summary["min_efficiency"] == pytest.approx(0.333333, abs=1e-6)
    assert summary["average_group_size"] == pytest.approx(3.333333, abs=1e-6)
    assert summary["max_group_size"] == 4


# --- run_all() is alias of run_deterministic() ---

def test_run_all_is_deterministic_alias(equipments):
    config = ProcessingConfig(
        algorithm="none",
        graph_min_shared_ratio=0.0,
        graph_min_shared_count=1,
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
    )
    master = RuneMaster(equipments, config=config)
    groups = master.run_all()
    assert len(groups) == 3
    assert all(g["selection_method"] == "deterministic" for g in groups)
