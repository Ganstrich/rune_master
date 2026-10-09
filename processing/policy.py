"""Single acceptance policy for candidate equipment groups."""

from typing import Any, Mapping

from processing.config_dataclass import ProcessingConfig


class GroupAcceptancePolicy:
    """Apply all configured admissibility thresholds exactly once."""

    def __init__(self, config: ProcessingConfig) -> None:
        self.min_size = config.group_min_size
        self.max_size = config.group_max_size
        self.min_shared_resources = config.group_min_shared_resources
        self.efficiency_threshold = config.group_efficiency_threshold
        self.quality_threshold = config.group_quality_threshold
        self.max_set_share = config.group_max_set_share
        self.max_line_items = config.max_line_items
        self.max_total_units = config.max_total_units
        # sharing_efficiency only discriminates on small groups: at group_size 2
        # it is exactly pairwise Jaccard, while only 8.5% of 4-item groups fall
        # below the floor. Gating the floor on group size keeps the check
        # meaningful without rejecting large cohesive groups (metrics-revision §3.6).
        self.efficiency_threshold_max_size = 3

    @classmethod
    def from_values(
        cls,
        min_size: int,
        max_size: int,
        min_shared_resources: int,
        efficiency_threshold: float,
        quality_threshold: float,
    ) -> "GroupAcceptancePolicy":
        """Build a policy for legacy mapper entry points with explicit thresholds."""
        policy = cls.__new__(cls)
        policy.min_size = min_size
        policy.max_size = max_size
        policy.min_shared_resources = min_shared_resources
        policy.efficiency_threshold = efficiency_threshold
        policy.quality_threshold = quality_threshold
        policy.max_set_share = 1.0
        policy.max_line_items = float("inf")
        policy.max_total_units = float("inf")
        policy.efficiency_threshold_max_size = 3
        return policy

    def rejection_reason(self, group: Mapping[str, Any]) -> str | None:
        """Return the first failed threshold, or ``None`` when accepted."""
        group_size = int(group.get("group_size", len(group.get("equipments", []))))
        if group_size < self.min_size or group_size > self.max_size:
            return "group_size"
        if int(group.get("shared_resources_count", 0)) < self.min_shared_resources:
            return "shared_resources_count"
        if group_size <= self.efficiency_threshold_max_size and (
            float(group.get("sharing_efficiency", 0.0)) < self.efficiency_threshold
        ):
            return "sharing_efficiency"
        if float(group.get("quality_score", 0.0)) < self.quality_threshold:
            return "quality_score"
        if float(group.get("largest_set_share", 0.0)) > self.max_set_share:
            return "largest_set_share"
        if int(group.get("unique_ingredients_count", 0)) > self.max_line_items:
            return "max_line_items"
        if int(group.get("total_items_needed", 0)) > self.max_total_units:
            return "max_total_units"
        return None

    def accepts(self, group: Mapping[str, Any]) -> bool:
        """Return whether a candidate group satisfies every threshold."""
        return self.rejection_reason(group) is None