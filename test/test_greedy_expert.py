"""Regression tests for the greedy objective-driven expert."""

from models import Equipment, ResourceRequirement
from processing.config_dataclass import ProcessingConfig
from processing.experts.greedy_expert import GreedyGroupingExpert


def make_equipment(
    equipment_id: int,
    recipe: list[tuple[int, int]],
    set_id: int | None = None,
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
        set_id=set_id,
    )


def _config(**overrides: object) -> ProcessingConfig:
    base = {
        "group_min_size": 2,
        "group_min_shared_resources": 1,
        "group_efficiency_threshold": 0.0,
        "group_quality_threshold": 0.0,
        "group_max_set_share": 0.5,
    }
    base.update(overrides)
    return ProcessingConfig(**base)


def test_greedy_groups_are_disjoint() -> None:
    """Overlapping proposals are penalised downstream, so groups must partition."""
    recipe = [(10, 2), (20, 2), (30, 2)]
    equipments = [make_equipment(i, recipe) for i in range(1, 7)]

    groups = GreedyGroupingExpert().discover_groups(equipments, _config())

    assigned = [e.ankama_id for group in groups for e in group["equipments"]]
    assert groups
    assert len(assigned) == len(set(assigned))


def test_greedy_refuses_groups_dominated_by_one_panoplie() -> None:
    """A pool that is entirely one set cannot produce an admissible group."""
    recipe = [(10, 2), (20, 2), (30, 2)]
    equipments = [make_equipment(i, recipe, set_id=7) for i in range(1, 7)]

    groups = GreedyGroupingExpert().discover_groups(equipments, _config())

    assert groups == []


def test_greedy_mixes_set_and_set_free_items_within_the_cap() -> None:
    """Set items may still be grouped when set-free items keep the share legal."""
    recipe = [(10, 2), (20, 2), (30, 2)]
    equipments = [
        make_equipment(1, recipe, set_id=7),
        make_equipment(2, recipe, set_id=7),
        make_equipment(3, recipe),
        make_equipment(4, recipe),
    ]

    groups = GreedyGroupingExpert().discover_groups(equipments, _config())

    assert groups
    for group in groups:
        assert group["largest_set_share"] <= 0.5
