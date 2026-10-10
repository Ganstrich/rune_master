from models import Equipment, ResourceRequirement
from processing.experts.random_group_builder import RandomGroupBuilder
from processing.valuation.objective import GroupCandidate, GroupObjective


class IdObjective(GroupObjective):
    def score(self, group: GroupCandidate) -> float:
        return float(sum(equipment.ankama_id for equipment in group.equipments))


def make_equipment(equipment_id: int) -> Equipment:
    return Equipment(
        ankama_id=equipment_id,
        type={"id": 1, "name": "test"},
        level=50,
        name=f"Equipment {equipment_id}",
        recipe=[ResourceRequirement(10, 1), ResourceRequirement(20, 1)],
    )


def test_random_companions_use_injected_objective_marginal() -> None:
    seed, lower, higher = (make_equipment(index) for index in (1, 2, 3))
    builder = RandomGroupBuilder(
        [seed, lower, higher], objective=IdObjective(), seed=1
    )

    companions = builder.find_companions(seed, [seed, lower, higher], min_shared_resources=2)

    assert [equipment.ankama_id for equipment in companions] == [3, 2]