"""Protocols and value objects for group objectives."""

from dataclasses import dataclass
from typing import Protocol

from models import Equipment


@dataclass(frozen=True)
class GroupCandidate:
    """An immutable group and the resources excluded from its score."""

    equipments: tuple[Equipment, ...]
    excluded_resource_ids: frozenset[int] = frozenset()

    def __init__(
        self,
        equipments: tuple[Equipment, ...] | list[Equipment],
        excluded_resource_ids: frozenset[int] | set[int] = frozenset(),
    ) -> None:
        object.__setattr__(self, "equipments", tuple(equipments))
        object.__setattr__(
            self, "excluded_resource_ids", frozenset(excluded_resource_ids)
        )

    def with_item(self, item: Equipment) -> "GroupCandidate":
        """Return a candidate containing one additional equipment item."""
        return GroupCandidate(self.equipments + (item,), self.excluded_resource_ids)


class GroupObjective(Protocol):
    """Score complete groups and their incremental item value."""

    def score(self, group: GroupCandidate) -> float:
        """Return the objective score for a complete candidate group."""
        ...

    def marginal(self, group: GroupCandidate, item: Equipment) -> float:
        """Return the score change from adding an item to a candidate."""
        return self.score(group.with_item(item)) - self.score(group)