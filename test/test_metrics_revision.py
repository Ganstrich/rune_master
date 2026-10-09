"""Tests for the metrics-revision implementation (snapshot 3.7.7.6, plans/metrics-revision.md)."""

import pytest

from models import Equipment, ResourceRequirement
from processing.config_dataclass import ProcessingConfig
from processing.equipment_filter import SetExclusionFilter
from processing.group_mapper import GroupMapper
from processing.policy import GroupAcceptancePolicy
from processing.quality_metrics import GroupQualityEvaluator, GroupQualityWeights


def make_equipment(
    ankama_id,
    recipe,
    set_id=None,
    level=50,
    type_name="test",
    stat_weight=100.0,
):
    return Equipment(
        ankama_id=ankama_id,
        type={"id": 1, "name": type_name},
        level=level,
        name=f"Equipment {ankama_id}",
        stat_weight=stat_weight,
        recipe=[
            ResourceRequirement(resource_id=resource_id, quantity=quantity)
            for resource_id, quantity in recipe
        ],
        set_id=set_id,
    )


# --- C2: set exclusion (metrics-revision §3.8) ---

def test_items_in_large_sets_are_excluded() -> None:
    # set_id=1 has five members -> the whole set is excluded.
    # set_id=2 has four members -> below the threshold, so kept.
    equipments = [
        make_equipment(1, [(10, 1)], set_id=1),
        make_equipment(2, [(10, 1)], set_id=1),
        make_equipment(3, [(10, 1)], set_id=1),
        make_equipment(4, [(10, 1)], set_id=1),
        make_equipment(5, [(10, 1)], set_id=1),
        make_equipment(6, [(20, 1)], set_id=2),
        make_equipment(7, [(20, 1)], set_id=2),
        make_equipment(8, [(20, 1)], set_id=2),
        make_equipment(9, [(20, 1)], set_id=2),
        make_equipment(10, [(30, 1)]),  # setless -> kept
    ]

    retained, excluded = SetExclusionFilter.exclude_panoplie_items(equipments, min_set_size=5)

    assert [e.ankama_id for e in retained] == [6, 7, 8, 9, 10]
    assert [e.ankama_id for e in excluded] == [1, 2, 3, 4, 5]


def test_small_sets_and_setless_items_are_retained() -> None:
    equipments = [
        make_equipment(1, [(10, 1)], set_id=1),
        make_equipment(2, [(10, 1)], set_id=1),
        make_equipment(3, [(10, 1)], set_id=1),
        make_equipment(4, [(10, 1)], set_id=1),
    ]

    retained, excluded = SetExclusionFilter.exclude_panoplie_items(equipments, min_set_size=5)

    assert len(retained) == 4
    assert excluded == []


def test_threshold_is_configurable_and_disableable() -> None:
    equipments = [
        make_equipment(1, [(10, 1)], set_id=1),
        make_equipment(2, [(10, 1)], set_id=1),
        make_equipment(3, [(10, 1)], set_id=1),
    ]

    # min_set_size=3 now drops all three
    retained, excluded = SetExclusionFilter.exclude_panoplie_items(equipments, min_set_size=3)
    assert retained == []
    assert len(excluded) == 3

    # 99 disables the filter entirely (the --no-set-filter override)
    retained, excluded = SetExclusionFilter.exclude_panoplie_items(equipments, min_set_size=99)
    assert len(retained) == 3
    assert excluded == []


def test_exclusion_is_reported_by_band_and_slot() -> None:
    """Metric N10: the cut must be visible so it cannot read as a coverage bug."""
    equipments = [
        make_equipment(1, [(10, 1)], set_id=1, level=45, type_name="hat"),
        make_equipment(2, [(10, 1)], set_id=1, level=85, type_name="boots"),
    ]

    report = SetExclusionFilter.summarize_excluded(equipments)

    assert report["total"] == 2
    assert report["by_band"] == {"band_2": 1, "band_4": 1}
    assert report["by_slot"] == {"hat": 1, "boots": 1}


def test_orchestrator_applies_set_exclusion() -> None:
    from processing.orchestrator import RuneMaster

    equipments = [
        make_equipment(1, [(10, 1)], set_id=1),
        make_equipment(2, [(10, 1)], set_id=1),
        make_equipment(3, [(10, 1)], set_id=1),
        make_equipment(4, [(10, 1)], set_id=1),
        make_equipment(5, [(10, 1)], set_id=1),  # 5-member set -> excluded
        make_equipment(6, [(20, 1)]),
        make_equipment(7, [(20, 1)]),
        make_equipment(8, [(20, 1)]),
        make_equipment(9, [(20, 1)]),  # 4-member set -> kept
        make_equipment(10, [(30, 1)]),  # setless -> kept
    ]

    master = RuneMaster(equipments, config=ProcessingConfig())

    assert [e.ankama_id for e in master.equipments] == [6, 7, 8, 9, 10]
    assert master.set_exclusion_report["total"] == 5


# --- Structure-aware splitter (metrics-revision §3.1 / FM1) ---

def test_splitter_produces_resource_cohesive_subgroups() -> None:
    """Contiguous slicing lost 100% of chunks to the policy (probe R1)."""
    mapper = GroupMapper([])
    # Three tight pairs sharing a resource each, with nothing in common.
    equipments = [
        make_equipment(1, [(10, 1), (11, 1)]),
        make_equipment(2, [(10, 1), (12, 1)]),
        make_equipment(3, [(20, 1), (21, 1)]),
        make_equipment(4, [(20, 1), (22, 1)]),
        make_equipment(5, [(30, 1), (31, 1)]),
        make_equipment(6, [(30, 1), (32, 1)]),
    ]

    subgroups = mapper._split_large_community(equipments, max_size=2)

    assert len(subgroups) == 3
    assert all(len(subgroup) == 2 for subgroup in subgroups)
    # Every subgroup must share at least one resource, which contiguous slicing
    # of a Louvain-ordered list does not guarantee.
    for subgroup in subgroups:
        sets = [set(r.resource_id for r in e.recipe) for e in subgroup]
        assert len(sets[0] & sets[1]) >= 1


def test_splitter_respects_max_size() -> None:
    mapper = GroupMapper([])
    equipments = [
        make_equipment(i, [(10, 1), (i + 100, 1)]) for i in range(1, 10)
    ]

    subgroups = mapper._split_large_community(equipments, max_size=4)

    assert all(len(subgroup) <= 4 for subgroup in subgroups)
    assert sum(len(subgroup) for subgroup in subgroups) == 9


def test_splitter_handles_small_community() -> None:
    mapper = GroupMapper([])
    equipments = [make_equipment(1, [(10, 1)])]

    assert mapper._split_large_community(equipments, max_size=8) == [equipments]


# --- Efficiency threshold rescoped to small groups (metrics-revision §3.6) ---

def base_group(size, efficiency=0.1, line_items=9, units=180):
    return {
        "group_size": size,
        "shared_resources_count": 3,
        "sharing_efficiency": efficiency,
        "quality_score": 0.5,
        "unique_ingredients_count": line_items,
        "total_items_needed": units,
    }


def test_efficiency_floor_still_applies_to_small_groups() -> None:
    policy = GroupAcceptancePolicy(ProcessingConfig())

    assert not policy.accepts(base_group(2, efficiency=0.1))
    assert policy.rejection_reason(base_group(2, efficiency=0.1)) == "sharing_efficiency"


def test_efficiency_floor_does_not_gate_large_groups() -> None:
    """Only 8.5% of 4-item groups fell below the floor, so it was near-inert."""
    policy = GroupAcceptancePolicy(ProcessingConfig())

    assert policy.accepts(base_group(8, efficiency=0.1))
    assert policy.rejection_reason(base_group(8, efficiency=0.1)) is None


def test_legacy_from_values_keeps_the_threshold_gate() -> None:
    policy = GroupAcceptancePolicy.from_values(2, 12, 3, 0.15, 0.0)

    assert not policy.accepts(base_group(2, efficiency=0.1))


# --- Objective term set (metrics-revision §6 step 5) ---

def test_resource_reuse_ratio_leaves_the_score_but_stays_reported() -> None:
    weights = GroupQualityWeights()

    assert weights.normalized()["resource_reuse_ratio"] == 0.0

    identical = [
        make_equipment(1, [(10, 2), (20, 3)]),
        make_equipment(2, [(10, 2), (20, 3)]),
    ]
    metrics = GroupQualityEvaluator().evaluate(identical)

    # Field still computed...
    assert metrics.resource_reuse_ratio == 1.0
    # ...but contributes nothing. Setless items score 0.6*compression(0.5)
    # + 0.2*shared_quantity(1.0) + 0.2*set_free(1.0) = 0.7.
    assert metrics.quality_score == pytest.approx(0.6 * 0.5 + 0.2 * 1.0 + 0.2 * 1.0)


# --- Config defaults (metrics-revision §3.1, §3.2, §3.3, §3.4, §3.8) ---

def test_config_defaults_match_the_revision() -> None:
    config = ProcessingConfig()

    assert config.max_line_items == 32
    assert config.max_total_units == 2000
    assert config.group_max_size == 12
    assert config.graph_min_shared_ratio == 0.15
    assert config.equipment_density_level_ratio == 2.0
    assert config.set_exclusion_min_size == 5


def test_dead_resource_is_removed_but_live_one_kept() -> None:
    """15263 has zero recipe entries of any subtype; 14635 is real."""
    config = ProcessingConfig()

    assert 15263 not in config.excluded_resource_ids
    assert 14635 in config.excluded_resource_ids


def test_max_level_default_is_200() -> None:
    from config import Config

    assert Config.MAX_LEVEL == 200
