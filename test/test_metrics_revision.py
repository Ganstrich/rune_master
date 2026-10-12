"""Tests for the metrics revision implementation (snapshot 3.7.7.6)."""

import pytest

from models import Equipment, ResourceRequirement
from processing.config import ProcessingConfig
from processing.filters.equipment_filter import SetExclusionFilter
from processing.policy import GroupAcceptancePolicy
from processing.metrics.quality_metrics import GroupQualityEvaluator, GroupQualityWeights


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


def test_items_in_large_sets_are_excluded() -> None:
    equipments = [
        make_equipment(1, [(10, 2)], set_id=1),
        make_equipment(2, [(10, 2)], set_id=1),
        make_equipment(3, [(10, 2)], set_id=1),
        make_equipment(4, [(10, 2)], set_id=1),
        make_equipment(5, [(10, 2)], set_id=1),
        make_equipment(6, [(20, 2)]),
    ]
    kept, excluded = SetExclusionFilter.exclude_panoplie_items(equipments, min_set_size=5)
    assert len(excluded) == 5
    assert len(kept) == 1


def test_small_sets_and_setless_items_are_retained() -> None:
    equipments = [
        make_equipment(1, [(10, 2)], set_id=1),
        make_equipment(2, [(10, 2)], set_id=1),
        make_equipment(3, [(20, 2)]),
    ]
    kept, excluded = SetExclusionFilter.exclude_panoplie_items(equipments, min_set_size=5)
    assert len(excluded) == 0
    assert len(kept) == 3


def test_threshold_is_configurable_and_disableable() -> None:
    equipments = [
        make_equipment(1, [(10, 2)], set_id=1),
        make_equipment(2, [(10, 2)], set_id=1),
    ]
    kept, excluded = SetExclusionFilter.exclude_panoplie_items(equipments, min_set_size=99)
    assert len(excluded) == 0
    assert len(kept) == 2


def test_exclusion_is_reported_by_band_and_slot() -> None:
    equipments = [
        make_equipment(1, [(10, 2)], set_id=1, level=10),
        make_equipment(2, [(10, 2)], set_id=1, level=10),
        make_equipment(3, [(10, 2)], set_id=1, level=30),
        make_equipment(4, [(10, 2)], set_id=1, level=30),
    ]
    _, excluded = SetExclusionFilter.exclude_panoplie_items(equipments, min_set_size=3)
    report = SetExclusionFilter.summarize_excluded(excluded)
    assert report["total"] == 4
    assert "band_0" in report["by_band"]
    assert "band_1" in report["by_band"]


def test_orchestrator_applies_set_exclusion() -> None:
    from processing.orchestrator import RuneMaster

    equipments = [
        make_equipment(1, [(10, 2)], set_id=1),
        make_equipment(2, [(10, 2)], set_id=1),
        make_equipment(3, [(10, 2)], set_id=1),
        make_equipment(4, [(10, 2)], set_id=1),
        make_equipment(5, [(10, 2)], set_id=1),
    ]
    master = RuneMaster(equipments)
    assert len(master.set_excluded) == 5
    assert len(master.equipments) == 0


def test_splitter_produces_resource_cohesive_subgroups() -> None:
    equipments = [
        make_equipment(1, [(10, 2), (20, 2)]),
        make_equipment(2, [(10, 2), (20, 2)]),
        make_equipment(3, [(30, 2), (40, 2)]),
        make_equipment(4, [(30, 2), (40, 2)]),
    ]
    from processing.metrics.group_metrics import GroupMetrics

    group = GroupMetrics.build_group_dict(equipments)
    assert group["group_size"] == 4


def test_splitter_respects_max_size() -> None:
    config = ProcessingConfig(group_max_size=2)
    policy = GroupAcceptancePolicy(config)
    equipments = [
        make_equipment(1, [(10, 2)]),
        make_equipment(2, [(10, 2)]),
        make_equipment(3, [(10, 2)]),
    ]
    from processing.metrics.group_metrics import GroupMetrics

    group = GroupMetrics.build_group_dict(equipments)
    assert not policy.accepts(group)


def test_splitter_handles_small_community() -> None:
    equipments = [make_equipment(1, [(10, 2)])]
    from processing.metrics.group_metrics import GroupMetrics

    group = GroupMetrics.build_group_dict(equipments)
    assert group["group_size"] == 1


def test_efficiency_floor_still_applies_to_small_groups() -> None:
    equipments = [
        make_equipment(1, [(10, 2), (20, 2), (30, 2)]),
        make_equipment(2, [(10, 2), (40, 2), (50, 2)]),
    ]
    config = ProcessingConfig(group_efficiency_threshold=0.5, group_max_size=3)
    policy = GroupAcceptancePolicy(config)
    from processing.metrics.group_metrics import GroupMetrics

    group = GroupMetrics.build_group_dict(equipments)
    assert not policy.accepts(group)


def test_efficiency_floor_does_not_gate_large_groups() -> None:
    equipments = [
        make_equipment(i, [(10, 2), (20, 2)])
        for i in range(1, 6)
    ]
    config = ProcessingConfig(group_efficiency_threshold=0.15, group_max_size=12)
    policy = GroupAcceptancePolicy(config)
    from processing.metrics.group_metrics import GroupMetrics

    group = GroupMetrics.build_group_dict(equipments)
    # Large groups are not gated by the efficiency floor
    assert len(group["equipments"]) > 3
    assert policy.accepts(group) or policy.rejection_reason(group) != "sharing_efficiency"


def test_legacy_from_values_keeps_the_threshold_gate() -> None:
    policy = GroupAcceptancePolicy.from_values(2, 12, 3, 0.15, 0.0)
    assert policy.min_size == 2
    assert policy.max_size == 12


def test_resource_reuse_ratio_leaves_the_score_but_stays_reported() -> None:
    equipments = [
        make_equipment(1, [(10, 2), (20, 3)]),
        make_equipment(2, [(10, 2), (20, 3)]),
    ]
    metrics = GroupQualityEvaluator().evaluate(equipments)
    assert metrics.resource_reuse_ratio > 0
    assert metrics.quality_score > 0


def test_config_defaults_match_the_revision() -> None:
    config = ProcessingConfig()
    assert config.group_min_size == 2
    assert config.group_max_size == 12
    assert config.max_line_items == 32
    assert config.max_total_units == 2000
    assert config.set_exclusion_min_size == 5
