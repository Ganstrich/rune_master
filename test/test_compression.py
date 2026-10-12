import pytest

from models import Equipment, ResourceRequirement
from processing.metrics.quality_metrics import GroupQualityEvaluator


def equipment(equipment_id: int, resources: list[int]) -> Equipment:
    return Equipment(
        equipment_id,
        {"id": 1, "name": "test"},
        1,
        f"Equipment {equipment_id}",
        recipe=[ResourceRequirement(resource_id, 1) for resource_id in resources],
    )


def test_compression_is_reported_and_subset_additions_do_not_lower_score() -> None:
    evaluator = GroupQualityEvaluator()
    base = [equipment(1, [1, 2]), equipment(2, [1, 3])]
    extended = base + [equipment(3, [1])]

    base_metrics = evaluator.evaluate(base)
    extended_metrics = evaluator.evaluate(extended)

    assert base_metrics.compression == pytest.approx(1 - 3 / 4)
    assert extended_metrics.quality_score >= base_metrics.quality_score
    assert extended_metrics.mean_pairwise_jaccard >= 0.0