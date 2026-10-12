"""RuneMaster: orchestrator for equipment group discovery.

Single-expert pipeline using the greedy grouping expert.
"""

from typing import Any, Dict, List, Optional

from models import Equipment
from processing.config import ProcessingConfig
from processing.experts.greedy_expert import GreedyGroupingExpert
from processing.filters.equipment_filter import SetExclusionFilter
from processing.policy import GroupAcceptancePolicy
from processing.metrics.selection import ProcessingReporter
from processing.valuation.overlap import OverlapObjective


class RuneMaster:
    """Orchestrator for equipment group discovery.

    Runs the greedy grouping expert on the equipment pool.
    """

    def __init__(
        self,
        equipments: List[Equipment],
        config: Optional[ProcessingConfig] = None,
        cache_manager=None,
        api_client=None,
    ):
        self.equipments = equipments
        self.config = config or ProcessingConfig()
        self.cache_manager = cache_manager
        self.api_client = api_client

        # Constraint C2: groups must not be built from panoplie items.
        self.equipments, self.set_excluded = SetExclusionFilter.exclude_panoplie_items(
            equipments, self.config.set_exclusion_min_size
        )
        self.set_exclusion_report = (
            SetExclusionFilter.summarize_excluded(self.set_excluded)
            if self.set_excluded
            else {}
        )

        self.objective = OverlapObjective(self.config.group_quality_weights)
        self.policy = GroupAcceptancePolicy(self.config)
        self.expert = GreedyGroupingExpert(
            cache_manager, api_client, self.objective, self.policy
        )

        self.groups: List[Dict[str, Any]] = []

    def run_greedy(self) -> List[Dict[str, Any]]:
        """Run greedy objective-driven grouping."""
        print("\n" + "=" * 60)
        print("🚀 RuneMaster: Greedy Pipeline (Greedy Expert)")
        print("=" * 60)

        self.groups = self.expert.discover_groups(self.equipments, self.config)
        self.print_summary()
        return self.groups

    def get_grouping_method(self) -> str:
        return self.config.grouping_method

    def get_summary(self) -> Dict[str, Any]:
        return ProcessingReporter(
            self.groups,
            len(self.equipments),
            self.config.portfolio_quality_weights,
        ).summary()

    def print_summary(self) -> None:
        ProcessingReporter(
            self.groups,
            len(self.equipments),
            self.config.portfolio_quality_weights,
        ).print_summary()
