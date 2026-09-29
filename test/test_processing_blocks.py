from models import Equipment, ResourceRequirement
from processing.blocks.recipes import iter_recipe, recipe_resource_ids
from processing.blocks.shopping_list import merge, resource_totals
from processing.blocks.similarity import jaccard


def test_jaccard_empty_disjoint_and_identical_sets() -> None:
    assert jaccard(set(), set()) == 0.0
    assert jaccard({1}, {2}) == 0.0
    assert jaccard({1, 2}, {1, 2}) == 1.0


def test_recipe_helpers_support_dataclass_and_dict_forms() -> None:
    equipment = Equipment(
        ankama_id=1,
        type=None,
        level=1,
        name="Test",
        recipe=[ResourceRequirement(10, 2)],
    )
    assert list(iter_recipe(equipment)) == [(10, 2)]
    assert recipe_resource_ids({"recipe": [{"item_ankama_id": 11, "quantity": 3}]}) == {11}


def test_shopping_list_helpers_aggregate_and_merge() -> None:
    equipment = {"recipe": [{"item_ankama_id": 10, "quantity": 2}]}
    assert resource_totals([equipment, equipment]) == {10: 4}
    assert merge({10: 2}, {10: 3, 11: 1}) == {10: 5, 11: 1}