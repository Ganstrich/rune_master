"""Price-independent quality features for equipment groups."""

from collections import defaultdict
from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any, Iterable, Mapping

from models import Equipment
from processing.blocks.similarity import jaccard


@dataclass(frozen=True)
class GroupQualityWeights:
    """Weights for the initial item-and-recipe-only quality heuristic."""

    resource_reuse_ratio: float = 0.30
    mean_pairwise_jaccard: float = 0.30
    overlapping_pair_ratio: float = 0.20
    shared_quantity_ratio: float = 0.20

    def normalized(self) -> dict[str, float]:
        """Return non-negative weights normalized to sum to one."""
        values = asdict(self)
        if any(value < 0 for value in values.values()):
            raise ValueError("Group quality weights must be non-negative")
        total = sum(values.values())
        if total <= 0:
            raise ValueError("At least one group quality weight must be positive")
        return {name: value / total for name, value in values.items()}


@dataclass(frozen=True)
class GroupQualityMetrics:
    """Observable recipe features and a transparent initial quality score."""

    group_size: int
    unique_resource_count: int
    shared_resource_count: int
    resource_occurrence_count: int
    repeated_resource_occurrence_count: int
    resource_reuse_ratio: float
    resource_reuse_depth: float
    shared_quantity_ratio: float
    mean_pairwise_jaccard: float
    minimum_pairwise_jaccard: float
    overlapping_pair_ratio: float
    quality_score: float

    def to_dict(self) -> dict[str, int | float]:
        """Return a serialization- and model-friendly feature dictionary."""
        return asdict(self)


class GroupQualityEvaluator:
    """Extract price-independent group features from equipment recipes."""

    def __init__(self, weights: GroupQualityWeights | None = None) -> None:
        self.weights = weights or GroupQualityWeights()

    def evaluate(
        self,
        equipments: Iterable[Equipment],
        excluded_resource_ids: set[int] | None = None,
    ) -> GroupQualityMetrics:
        """Calculate recipe reuse, cohesion, and quantity concentration features."""
        equipment_list = list(equipments)
        excluded = excluded_resource_ids or set()
        resource_sets: list[set[int]] = []
        resource_usage: dict[int, int] = defaultdict(int)
        resource_quantities: dict[int, int] = defaultdict(int)

        for equipment in equipment_list:
            quantities = self._resource_quantities(equipment, excluded)
            resources = set(quantities)
            resource_sets.append(resources)
            for resource_id in resources:
                resource_usage[resource_id] += 1
                resource_quantities[resource_id] += quantities[resource_id]

        unique_count = len(resource_usage)
        shared_resources = {
            resource_id
            for resource_id, usage_count in resource_usage.items()
            if usage_count >= 2
        }
        occurrence_count = sum(resource_usage.values())
        repeated_occurrences = sum(
            max(usage_count - 1, 0) for usage_count in resource_usage.values()
        )
        group_size = len(equipment_list)

        reuse_ratio = len(shared_resources) / unique_count if unique_count else 0.0
        reuse_depth_denominator = unique_count * max(group_size - 1, 0)
        reuse_depth = (
            repeated_occurrences / reuse_depth_denominator
            if reuse_depth_denominator
            else 0.0
        )

        total_quantity = sum(resource_quantities.values())
        shared_quantity = sum(
            resource_quantities[resource_id] for resource_id in shared_resources
        )
        shared_quantity_ratio = shared_quantity / total_quantity if total_quantity else 0.0

        similarities = [
            jaccard(left, right)
            for left, right in combinations(resource_sets, 2)
        ]
        mean_pairwise = sum(similarities) / len(similarities) if similarities else 0.0
        minimum_pairwise = min(similarities, default=0.0)
        overlapping_pair_ratio = (
            sum(similarity > 0 for similarity in similarities) / len(similarities)
            if similarities
            else 0.0
        )

        features = {
            "resource_reuse_ratio": reuse_ratio,
            "mean_pairwise_jaccard": mean_pairwise,
            "overlapping_pair_ratio": overlapping_pair_ratio,
            "shared_quantity_ratio": shared_quantity_ratio,
        }
        quality_score = sum(
            features[name] * weight
            for name, weight in self.weights.normalized().items()
        )

        return GroupQualityMetrics(
            group_size=group_size,
            unique_resource_count=unique_count,
            shared_resource_count=len(shared_resources),
            resource_occurrence_count=occurrence_count,
            repeated_resource_occurrence_count=repeated_occurrences,
            resource_reuse_ratio=reuse_ratio,
            resource_reuse_depth=reuse_depth,
            shared_quantity_ratio=shared_quantity_ratio,
            mean_pairwise_jaccard=mean_pairwise,
            minimum_pairwise_jaccard=minimum_pairwise,
            overlapping_pair_ratio=overlapping_pair_ratio,
            quality_score=quality_score,
        )

    @staticmethod
    def _resource_quantities(
        equipment: Equipment, excluded_resource_ids: set[int]
    ) -> dict[int, int]:
        quantities: dict[int, int] = defaultdict(int)
        for requirement in equipment.recipe or []:
            resource_id = int(requirement.resource_id)
            if resource_id not in excluded_resource_ids:
                quantities[resource_id] += max(int(requirement.quantity), 0)
        return dict(quantities)

@dataclass(frozen=True)
class PortfolioQualityWeights:
    """Weights for comparing complete grouping algorithm outputs."""

    group_quality: float = 0.65
    equipment_coverage: float = 0.35
    assignment_overlap_penalty: float = 0.50

    def normalized_rewards(self) -> tuple[float, float]:
        """Return normalized reward weights without changing the penalty."""
        if min(
            self.group_quality,
            self.equipment_coverage,
            self.assignment_overlap_penalty,
        ) < 0:
            raise ValueError("Portfolio quality weights must be non-negative")
        total = self.group_quality + self.equipment_coverage
        if total <= 0:
            raise ValueError("At least one portfolio reward weight must be positive")
        return self.group_quality / total, self.equipment_coverage / total


@dataclass(frozen=True)
class PortfolioQualityMetrics:
    """Coverage, redundancy, and quality metrics for an algorithm result."""

    group_count: int
    total_assignments: int
    unique_equipment_count: int
    duplicate_assignment_count: int
    equipment_coverage_rate: float
    assignment_overlap_rate: float
    mean_group_quality: float
    assignment_weighted_group_quality: float
    mean_group_overlap: float
    maximum_group_overlap: float
    portfolio_quality_score: float

    def to_dict(self) -> dict[str, int | float]:
        """Return a serialization- and model-friendly metric dictionary."""
        return asdict(self)


class PortfolioQualityEvaluator:
    """Evaluate a complete set of proposed groups without double-counting coverage."""

    def __init__(self, weights: PortfolioQualityWeights | None = None) -> None:
        self.weights = weights or PortfolioQualityWeights()

    def evaluate(
        self,
        groups: Iterable[Mapping[str, Any]],
        total_equipment_count: int,
    ) -> PortfolioQualityMetrics:
        """Calculate algorithm-level quality, unique coverage, and redundancy."""
        group_list = list(groups)
        equipment_sets = [
            {int(equipment.ankama_id) for equipment in group.get("equipments", [])}
            for group in group_list
        ]
        total_assignments = sum(len(equipment_ids) for equipment_ids in equipment_sets)
        unique_ids = set().union(*equipment_sets) if equipment_sets else set()
        unique_count = len(unique_ids)
        duplicate_count = max(total_assignments - unique_count, 0)
        coverage = (
            unique_count / total_equipment_count if total_equipment_count > 0 else 0.0
        )
        assignment_overlap = (
            duplicate_count / total_assignments if total_assignments else 0.0
        )

        qualities = [
            float(group.get("quality_score", 0.0)) for group in group_list
        ]
        mean_quality = sum(qualities) / len(qualities) if qualities else 0.0
        weighted_quality = (
            sum(quality * len(equipment_ids) for quality, equipment_ids in zip(
                qualities, equipment_sets
            ))
            / total_assignments
            if total_assignments
            else 0.0
        )

        group_overlaps = [
            jaccard(left, right)
            for left, right in combinations(equipment_sets, 2)
        ]
        mean_overlap = (
            sum(group_overlaps) / len(group_overlaps) if group_overlaps else 0.0
        )
        maximum_overlap = max(group_overlaps, default=0.0)

        quality_weight, coverage_weight = self.weights.normalized_rewards()
        score = (
            weighted_quality * quality_weight
            + coverage * coverage_weight
            - assignment_overlap * self.weights.assignment_overlap_penalty
        )
        score = min(max(score, 0.0), 1.0)

        return PortfolioQualityMetrics(
            group_count=len(group_list),
            total_assignments=total_assignments,
            unique_equipment_count=unique_count,
            duplicate_assignment_count=duplicate_count,
            equipment_coverage_rate=coverage,
            assignment_overlap_rate=assignment_overlap,
            mean_group_quality=mean_quality,
            assignment_weighted_group_quality=weighted_quality,
            mean_group_overlap=mean_overlap,
            maximum_group_overlap=maximum_overlap,
            portfolio_quality_score=score,
        )
