"""The current price-independent overlap objective."""

from processing.quality_metrics import GroupQualityEvaluator, GroupQualityWeights
from processing.valuation.objective import GroupCandidate, GroupObjective


class OverlapObjective(GroupObjective):
    """Score groups using the compression-oriented overlap metric."""

    def __init__(self, weights: GroupQualityWeights | None = None) -> None:
        self.evaluator = GroupQualityEvaluator(weights)

    def score(self, group: GroupCandidate) -> float:
        """Return the existing quality score for a candidate group."""
        metrics = self.evaluator.evaluate(
            group.equipments, set(group.excluded_resource_ids)
        )
        return metrics.quality_score
