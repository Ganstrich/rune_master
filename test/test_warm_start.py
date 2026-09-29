from models import Equipment, ResourceRequirement
from processing.config_dataclass import ProcessingConfig
from processing.experts.genetic_expert import GeneticGroupingExpert
from processing.valuation.objective import GroupCandidate, GroupObjective


class ConstantObjective(GroupObjective):
    def score(self, group: GroupCandidate) -> float:
        return float(len(group.equipments))


def test_genetic_expert_can_warm_start_and_record_provenance() -> None:
    equipments = [
        Equipment(
            index,
            {"id": 1},
            20,
            f"Equipment {index}",
            recipe=[ResourceRequirement(10, 1), ResourceRequirement(20 + index, 1)],
        )
        for index in range(1, 4)
    ]
    stored = [{"equipments": equipments[:2]}]
    config = ProcessingConfig(
        algorithm="none",
        graph_min_shared_ratio=0.0,
        group_min_shared_resources=1,
        group_efficiency_threshold=0.0,
        genetic_population_size=2,
        genetic_generations=1,
        random_seed=4,
    )
    expert = GeneticGroupingExpert(
        objective=ConstantObjective(), initial_groups=stored
    )

    groups = expert.discover_groups(equipments, config)

    assert groups
    assert all(group["provenance"] == "newly_discovered" for group in groups)

    evolved = expert.evolve_portfolio(stored, config)
    assert all(group["provenance"] == "evolved" for group in evolved)