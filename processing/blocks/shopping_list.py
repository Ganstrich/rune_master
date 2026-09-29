"""Pure shopping-list arithmetic."""

from collections.abc import Iterable, Mapping

from processing.blocks.recipes import iter_recipe


def resource_totals(equipments: Iterable[object]) -> dict[int, int]:
    """Aggregate recipe quantities by resource ID."""
    totals: dict[int, int] = {}
    for equipment in equipments:
        for resource_id, quantity in iter_recipe(equipment):
            totals[resource_id] = totals.get(resource_id, 0) + quantity
    return totals


def merge(*shopping_lists: Mapping[int, int]) -> dict[int, int]:
    """Merge resource quantity mappings into one shopping list."""
    merged: dict[int, int] = {}
    for shopping_list in shopping_lists:
        for resource_id, quantity in shopping_list.items():
            merged[resource_id] = merged.get(resource_id, 0) + quantity
    return merged