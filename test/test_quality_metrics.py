"""Regression tests for price-independent group and portfolio quality metrics."""

import pytest

from models import Equipment, ResourceRequirement
from processing import (
    GroupQualityEvaluator,
    PortfolioQualityEvaluator,
    ProcessingConfig,
)
from processing.experts.graph_expert import GraphGroupingExpert
from processing.experts.random_expert import RandomGroupingExpert
from processing.group_metrics import GroupMetrics


def make_equipment(
    equipment_id: int,
    recipe: list[tuple[int, int]],
) -> Equipment:
    """Create one minimal equipment record with a normalized recipe."""
    return Equipment(
        ankama_id=equipment_id,
        type={"id": 1, "name": "test"},
        level=50,
        name=f"Equipment {equipment_id}",
        stat_weight=100.0,
        recipe=[
            ResourceRequirement(resource_id=resource_id, quantity=quantity)
            for resource_id, quantity in recipe
        ],
    )


def test_group_quality_has_interpretable_boundary_values() -> None:
    """Identical recipes score below one because compression is size-aware."""
    identical = [
        make_equipment(1, [(10, 2), (20, 3)]),
        make_equipment(2, [(10, 2), (20, 3)]),
    ]
    disjoint = [
        make_equipment(3, [(30, 2)]),
        make_equipment(4, [(40, 2)]),
    ]

    evaluator = GroupQualityEvaluator()
    identical_metrics = evaluator.evaluate(identical)
    disjoint_metrics = evaluator.evaluate(disjoint)

    assert identical_metrics.quality_score == pytest.approx(0.75)
    assert identical_metrics.resource_reuse_depth == pytest.approx(1.0)
    assert disjoint_metrics.quality_score == pytest.approx(0.0)


def test_group_quality_excludes_configured_resources_from_all_features() -> None:
    """Common filler resources should not improve any quality component."""
    equipments = [
        make_equipment(1, [(99, 100), (10, 1)]),
        make_equipment(2, [(99, 100), (20, 1)]),
    ]

    metrics = GroupQualityEvaluator().evaluate(equipments, {99})

    assert metrics.shared_resource_count == 0
    assert metrics.shared_quantity_ratio == 0.0
    assert metrics.mean_pairwise_jaccard == 0.0
    assert metrics.quality_score == 0.0


def test_shared_quantity_ratio_uses_recipe_quantities() -> None:
    """Quantity concentration should be observable without changing set overlap."""
    low_quantity = [
        make_equipment(1, [(10, 1), (11, 10)]),
        make_equipment(2, [(10, 1), (12, 10)]),
    ]
    high_quantity = [
        make_equipment(3, [(10, 10), (11, 1)]),
        make_equipment(4, [(10, 10), (12, 1)]),
    ]

    evaluator = GroupQualityEvaluator()
    low_metrics = evaluator.evaluate(low_quantity)
    high_metrics = evaluator.evaluate(high_quantity)

    assert low_metrics.resource_reuse_ratio == high_metrics.resource_reuse_ratio
    assert low_metrics.mean_pairwise_jaccard == high_metrics.mean_pairwise_jaccard
    assert high_metrics.shared_quantity_ratio > low_metrics.shared_quantity_ratio
    assert high_metrics.quality_score > low_metrics.quality_score


def test_portfolio_coverage_does_not_double_count_equipment() -> None:
    """Repeated groups should increase overlap, not unique equipment coverage."""
    equipments = [
        make_equipment(1, [(10, 1)]),
        make_equipment(2, [(10, 1)]),
    ]
    group = GroupMetrics.build_group_dict(equipments)

    metrics = PortfolioQualityEvaluator().evaluate([group, group], 2)

    assert metrics.total_assignments == 4
    assert metrics.unique_equipment_count == 2
    assert metrics.equipment_coverage_rate == 1.0
    assert metrics.duplicate_assignment_count == 2
    assert metrics.assignment_overlap_rate == 0.5
    assert metrics.maximum_group_overlap == 1.0


def test_random_expert_enforces_common_quality_thresholds() -> None:
    """Random proposals should obey the same final filters as graph proposals."""
    first_recipe = [(1, 1), (2, 1), (3, 1)] + [
        (resource_id, 1) for resource_id in range(10, 17)
    ]
    second_recipe = [(1, 1), (2, 1), (3, 1)] + [
        (resource_id, 1) for resource_id in range(20, 27)
    ]
    equipments = [
        make_equipment(1, first_recipe),
        make_equipment(2, second_recipe),
    ]
    config = ProcessingConfig(
        group_min_shared_resources=3,
        group_efficiency_threshold=0.9,
        use_density_filtering=False,
        random_group_count=2,
        random_seed=1,
    )

    groups = RandomGroupingExpert().discover_groups(equipments, config)

    assert groups == []


def test_bilouvain_uses_bipartite_graph_and_returns_equipment_groups() -> None:
    """BiLouvain should project recipes and return equipment-only groups."""
    equipments = [
        make_equipment(1, [(10, 1), (20, 1)]),
        make_equipment(2, [(10, 1), (30, 1)]),
        make_equipment(3, [(10, 1), (40, 1)]),
    ]
    config = ProcessingConfig(
        algorithm="bilouvain",
        resolution_range=(1, 2, 1),
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
        random_seed=7,
    )

    groups = GraphGroupingExpert().discover_groups(equipments, config)

    assert groups
    assert {
        equipment.ankama_id
        for group in groups
        for equipment in group["equipments"]
    } <= {1, 2, 3}