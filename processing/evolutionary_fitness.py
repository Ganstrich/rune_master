"""Portfolio fitness evaluation for evolutionary search."""
from typing import Any, Dict, List, Optional, Set

from processing.evolutionary_search_state import PortfolioCandidate
from processing.policy import GroupAcceptancePolicy
from processing.quality_metrics import PortfolioQualityEvaluator
from processing.valuation.objective import GroupCandidate, GroupObjective


class PortfolioFitnessEvaluator:
    """Evaluate fitness of complete portfolios (not just sum of groups).

    Uses the canonical portfolio evaluator to score coverage, overlap, and quality
    at the portfolio level, ensuring diversity and balanced coverage.
    """

    def __init__(
        self,
        total_equipment_count: int,
        portfolio_weights=None,
        objective: Optional[GroupObjective] = None,
        policy: Optional[GroupAcceptancePolicy] = None,
    ):
        self.total_equipment_count = total_equipment_count
        self.evaluator = PortfolioQualityEvaluator(portfolio_weights)
        self.objective = objective
        self.policy = policy

    def evaluate(
        self,
        candidate: PortfolioCandidate,
        excluded_resource_ids: Optional[Set[int]] = None,
    ) -> PortfolioCandidate:
        """Re-evaluate a portfolio and return updated candidate with metrics.

        Returns a new PortfolioCandidate with:
        - Updated score from portfolio-level evaluation
        - Feasibility status and rejection reason (if policy rejects it)
        - Portfolio metrics captured in 'metrics' field
        """
        if not candidate.groups:
            return PortfolioCandidate(
                groups=(),
                score=-100.0,
                feasibility_status="rejected",
                rejection_reason="Empty portfolio",
                provenance=candidate.provenance,
                generation=candidate.generation,
                parent_ids=candidate.parent_ids,
                metadata=candidate.metadata,
            )

        # Evaluate each group under the objective if available
        group_scores = []
        for group in candidate.groups:
            if self.objective is not None:
                eq_list = list(group.get("equipments", []))
                group_cand = GroupCandidate(eq_list, excluded_resource_ids or set())
                score = self.objective.score(group_cand)
            else:
                score = float(group.get("quality_score", 0.0))
            group_scores.append(score)

        # Evaluate portfolio as a whole
        portfolio_metrics = self.evaluator.evaluate(
            candidate.groups, self.total_equipment_count
        )

        # Combine group quality with portfolio coverage and overlap penalties
        # Portfolio score emphasizes coverage and penalizes duplication
        portfolio_score = portfolio_metrics.portfolio_quality_score

        # Check feasibility against policy
        feasibility_status = "accepted"
        rejection_reason = None
        if self.policy is not None:
            for group in candidate.groups:
                if not self.policy.accepts(group):
                    feasibility_status = "rejected"
                    rejection_reason = f"Group rejected: {group.get('group_size', 0)} items"
                    break

        metrics_dict = portfolio_metrics.to_dict()
        metrics_dict["group_scores"] = group_scores
        metrics_dict["mean_group_score"] = (
            sum(group_scores) / len(group_scores) if group_scores else 0.0
        )

        return PortfolioCandidate(
            groups=candidate.groups,
            score=portfolio_score,
            metrics=metrics_dict,
            generation=candidate.generation,
            parent_ids=candidate.parent_ids,
            provenance=candidate.provenance,
            fingerprint=candidate.fingerprint or PortfolioCandidate.compute_fingerprint(
                list(candidate.groups)
            ),
            feasibility_status=feasibility_status,
            rejection_reason=rejection_reason,
            metadata=candidate.metadata,
        )
