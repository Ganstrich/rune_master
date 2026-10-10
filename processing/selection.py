"""Processing report helpers."""

from typing import Any

from processing.quality_metrics import PortfolioQualityEvaluator


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