"""Pure shopping-list arithmetic."""
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from models import Equipment
from processing.blocks.recipes import iter_recipe, recipe_resource_ids


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


@dataclass(frozen=True)
class ShoppingList:
    """The list of components needed for a set of items."""

    totals: dict[int, int] = field(default_factory=dict)
    individual_resource_counts: tuple[int, ...] = ()

    @property
    def line_item_count(self) -> int:
        """Return the number of distinct resources needed."""
        return len(self.totals)

    @property
    def total_units(self) -> int:
        """Return the total quantity across all resources."""
        return sum(self.totals.values())

    @property
    def compression(self) -> float:
        """Return 1 - |union| / sum(|individual|).

        Measures how much the shopping list is compressed by sharing
        resources across items.  0 means no sharing (every item uses
        completely distinct resources); approaches 1 as items share more.
        """
        individual_sum = sum(self.individual_resource_counts)
        if individual_sum == 0:
            return 0.0
        return 1.0 - len(self.totals) / individual_sum

    @classmethod
    def from_equipments(
        cls, equipments: Iterable[Equipment | dict]
    ) -> "ShoppingList":
        """Build a ShoppingList from equipment objects."""
        totals: dict[int, int] = {}
        individual_counts: list[int] = []
        for equipment in equipments:
            resource_ids = recipe_resource_ids(equipment)
            individual_counts.append(len(resource_ids))
            for resource_id, quantity in iter_recipe(equipment):
                totals[resource_id] = totals.get(resource_id, 0) + quantity
        return cls(
            totals=totals,
            individual_resource_counts=tuple(individual_counts),
        )

    def merge(self, other: "ShoppingList") -> "ShoppingList":
        """Merge two shopping lists into one."""
        merged_totals = dict(self.totals)
        for resource_id, quantity in other.totals.items():
            merged_totals[resource_id] = merged_totals.get(resource_id, 0) + quantity
        return ShoppingList(
            totals=merged_totals,
            individual_resource_counts=(
                self.individual_resource_counts + other.individual_resource_counts
            ),
        )
