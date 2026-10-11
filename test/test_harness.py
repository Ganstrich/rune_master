from processing.config import ProcessingConfig
from processing.tools.harness import run_comparison
from models import Equipment, ResourceRequirement


def make_equipments() -> list[Equipment]:
    return [
        Equipment(
            index,
            {"id": 1},
            20 + index,
            f"Equipment {index}",
            stat_weight=10 + index,
            recipe=[ResourceRequirement(100, 2), ResourceRequirement(200 + index, 1)],
        )
        for index in range(1, 5)
    ]


def test_baseline_comparison_is_repeatable() -> None:
    config = ProcessingConfig(
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
    )
    first = run_comparison(make_equipments(), ("greedy",), config)
    second = run_comparison(make_equipments(), ("greedy",), config)

    for row in first + second:
        row.pop("runtime_seconds")
    assert first == second