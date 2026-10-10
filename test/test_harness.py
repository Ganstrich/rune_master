from processing.config_dataclass import ProcessingConfig
from processing.harness import run_comparison
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


def test_baseline_comparison_is_repeatable_for_fixed_seed() -> None:
    config = ProcessingConfig(
        algorithm="none",
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
        random_seed=7,
        genetic_generations=1,
        genetic_population_size=2,
    )
    first = run_comparison(make_equipments(), config, ("greedy", "random"))
    second = run_comparison(make_equipments(), config, ("greedy", "random"))

    for row in first + second:
        row.pop("runtime_seconds")
    assert first == second