"""Pure recipe normalization helpers."""

from collections.abc import Iterable, Iterator
from typing import Any

from models import Equipment, ResourceRequirement


def iter_recipe(equipment: Equipment | dict[str, Any]) -> Iterator[tuple[int, int]]:
    """Yield normalized resource ID and quantity pairs from an equipment recipe."""
    recipe: Iterable[Any]
    if isinstance(equipment, Equipment):
        recipe = equipment.recipe or []
    else:
        recipe = equipment.get("recipe") or []

    for requirement in recipe:
        if isinstance(requirement, ResourceRequirement):
            yield requirement.resource_id, requirement.quantity
            continue
        if isinstance(requirement, dict):
            try:
                yield int(requirement.get("item_ankama_id")), int(
                    requirement.get("quantity", 1)
                )
            except (TypeError, ValueError):
                continue
            continue

        resource_id = getattr(requirement, "resource_id", None) or getattr(
            requirement, "item_ankama_id", None
        )
        quantity = getattr(requirement, "quantity", 1)
        if resource_id is not None:
            yield int(resource_id), int(quantity)


def recipe_resource_ids(equipment: Equipment | dict[str, Any]) -> set[int]:
    """Return distinct resource IDs used by an equipment recipe."""
    return {resource_id for resource_id, _quantity in iter_recipe(equipment)}