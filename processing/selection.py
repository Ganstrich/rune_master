"""Portfolio proposal selection and reporting helpers."""

from collections.abc import Iterable, Mapping
from typing import Any

from processing.blocks.similarity import jaccard
from processing.quality_metrics import PortfolioQualityEvaluator


class PortfolioSelector:
    """Select a non-duplicated portfolio from scored expert proposals."""

    @staticmethod
    def select(
        proposals: Iterable[dict[str, Any]], overlap_threshold: float
    ) -> list[dict[str, Any]]:
        """Preserve the committee's score order and greedy deduplication."""
        ordered = sorted(
            proposals, key=lambda proposal: proposal.get("fitness_score", 0), reverse=True
        )
        selected: list[dict[str, Any]] = []
        for proposal in ordered:
            if len(proposal.get("equipments", [])) < 2:
                continue
            if any(
                jaccard(
                    {item.ankama_id for item in proposal["equipments"]},
                    {item.ankama_id for item in existing["equipments"]},
                )
                >= overlap_threshold
                for existing in selected
            ):
                continue
            selected.append(proposal)
        return selected


class ProcessingReporter:
    """Build and print the existing processing summaries."""

    def __init__(self, groups: list[dict[str, Any]], equipment_count: int, weights) -> None:
        self.groups = groups
        self.equipment_count = equipment_count
        self.weights = weights

    def summary(self) -> dict[str, Any]:
        if not self.groups:
            return {}
        portfolio = PortfolioQualityEvaluator(self.weights).evaluate(
            self.groups, self.equipment_count
        )
        total_assignments = portfolio.total_assignments
        efficiencies = [group["sharing_efficiency"] for group in self.groups]
        group_sizes = [len(group["equipments"]) for group in self.groups]
        return {
            "total_groups": len(self.groups),
            "total_equipment_in_groups": total_assignments,
            "unique_equipment_in_groups": portfolio.unique_equipment_count,
            "total_equipment": self.equipment_count,
            "retention_rate": portfolio.equipment_coverage_rate,
            "equipment_coverage_rate": portfolio.equipment_coverage_rate,
            "duplicate_assignment_count": portfolio.duplicate_assignment_count,
            "assignment_overlap_rate": portfolio.assignment_overlap_rate,
            "average_efficiency": sum(efficiencies) / len(efficiencies),
            "average_quality_score": portfolio.mean_group_quality,
            "assignment_weighted_quality_score": portfolio.assignment_weighted_group_quality,
            "mean_group_overlap": portfolio.mean_group_overlap,
            "maximum_group_overlap": portfolio.maximum_group_overlap,
            "portfolio_quality_score": portfolio.portfolio_quality_score,
            "max_efficiency": max(efficiencies, default=0),
            "min_efficiency": min(efficiencies, default=0),
            "average_group_size": total_assignments / len(self.groups),
            "max_group_size": max(group_sizes, default=0),
        }

    def print_summary(self) -> None:
        summary = self.summary()
        if not summary:
            print("No groups generated")
            return
        print("\n" + "=" * 60)
        print("📈 COMMITTEE SUMMARY")
        print("=" * 60)
        print(f"Total Groups:           {summary['total_groups']}")
        print(f"Total Equipment:        {summary['total_equipment']}")
        print(f"Equipment Assignments:  {summary['total_equipment_in_groups']}")
        print(f"Unique Equipment:       {summary['unique_equipment_in_groups']}")
        print(f"Equipment Coverage:     {summary['equipment_coverage_rate']:.1%}")
        print(f"Assignment Overlap:     {summary['assignment_overlap_rate']:.1%}")
        print(f"Avg Group Size:         {summary['average_group_size']:.1f}")
        print(f"Average Group Quality:  {summary['average_quality_score']:.1%}")
        print(f"Portfolio Quality:      {summary['portfolio_quality_score']:.1%}")
        print(f"Average Efficiency:     {summary['average_efficiency']:.1%}")
        print(
            f"Efficiency Range:       {summary['min_efficiency']:.1%} - {summary['max_efficiency']:.1%}"
        )
        print("=" * 60 + "\n")