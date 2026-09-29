import pytest

from models import Equipment, ResourceRequirement
from processing.quality_metrics import GroupQualityEvaluator, GroupQualityWeights
from processing.valuation.objective import GroupCandidate, GroupObjective
from processing.valuation.overlap import OverlapObjective


def make_equipment(equipment_id: int, recipe: list[tuple[int, int]]) -> Equipment:
    return Equipment(
        ankama_id=equipment_id,
        type={"id": 1, "name": "test"},
        level=50,
        name=f"Equipment {equipment_id}",
        recipe=[ResourceRequirement(resource_id, quantity) for resource_id, quantity in recipe],
    )


def test_overlap_objective_matches_quality_evaluator() -> None:
    equipments = [
        make_equipment(1, [(10, 2), (20, 1)]),
        make_equipment(2, [(10, 4), (30, 3)]),
    ]
    weights = GroupQualityWeights(
        resource_reuse_ratio=0.2,
        mean_pairwise_jaccard=0.4,
        overlapping_pair_ratio=0.1,
        shared_quantity_ratio=0.3,
    )
    candidate = GroupCandidate(equipments, {10})

    expected = GroupQualityEvaluator(weights).evaluate(equipments, {10}).quality_score

    assert OverlapObjective(weights).score(candidate) == pytest.approx(expected)


def test_protocol_default_marginal_is_score_difference() -> None:
    class TestObjective(GroupObjective):
        def score(self, group: GroupCandidate) -> float:
            return float(len(group.equipments) ** 2)

    objective: GroupObjective = TestObjective()
    group = GroupCandidate([make_equipment(1, [])])
    item = make_equipment(2, [])

    assert objective.marginal(group, item) == pytest.approx(
        objective.score(group.with_item(item)) - objective.score(group)
    )