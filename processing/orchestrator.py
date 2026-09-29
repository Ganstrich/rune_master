"""RuneMaster: Main orchestrator for equipment group processing pipeline.

This is the central hub that coordinates different GroupingExperts
as a Mixture of Experts (MoE) committee.
"""

from typing import Any, Dict, List, Optional

from models import Equipment
from processing.config_dataclass import ProcessingConfig
from processing.experts.genetic_expert import GeneticGroupingExpert
from processing.experts.graph_expert import GraphGroupingExpert
from processing.experts.random_expert import RandomGroupingExpert
from processing.experts.baseline_expert import BaselineExpert
from processing.graph_builder import GraphBuilder
from processing.policy import GroupAcceptancePolicy
from processing.selection import PortfolioSelector, ProcessingReporter
from processing.valuation.objective import GroupCandidate
from processing.valuation.overlap import OverlapObjective


class RuneMaster:
    """Orchestrator for equipment group discovery and optimization.

    Acts as a Gating Network that coordinates specialized GroupingExperts.
    """

    def __init__(
        self,
        equipments: List[Equipment],
        config: Optional[ProcessingConfig] = None,
        cache_manager=None,
        api_client=None,
    ):
        """Initialize RuneMaster.

        Args:
            equipments: List of all Equipment objects
            config: ProcessingConfig for pipeline behavior
            cache_manager: Optional CacheManager for resource name lookup
            api_client: Optional API client to fetch resource names
        """
        self.equipments = equipments
        self.config = config or ProcessingConfig()
        self.cache_manager = cache_manager
        self.api_client = api_client

        self.objective = OverlapObjective(self.config.group_quality_weights)
        self.policy = GroupAcceptancePolicy(self.config)
        # Initialize Experts
        self.experts = {
            "deterministic": GraphGroupingExpert(
                cache_manager, api_client, self.objective, self.policy
            ),
            "random": RandomGroupingExpert(
                cache_manager, api_client, self.objective, self.policy
            ),
            "genetic": GeneticGroupingExpert(
                cache_manager, api_client, objective=self.objective, policy=self.policy
            ),
            "baseline": BaselineExpert(
                cache_manager, api_client, self.objective, self.policy
            ),
        }

        # Results
        self.groups: List[Dict[str, Any]] = []
        self.expert_failures: Dict[str, str] = {}

    def run_all(self) -> List[Dict[str, Any]]:
        """Run the default pipeline (backward compatibility)."""
        return self.run_deterministic()

    def run_baseline(self) -> List[Dict[str, Any]]:
        """Run the objective-driven baseline expert."""
        self.groups = self.experts["baseline"].discover_groups(self.equipments, self.config)
        self.print_summary()
        return self.groups

    def run_deterministic(self) -> List[Dict[str, Any]]:
        """Run pure graph-based grouping."""
        print("\n" + "=" * 60)
        print("🚀 RuneMaster: Deterministic Pipeline (Graph Expert)")
        print("=" * 60)

        expert = self.experts["deterministic"]
        self.groups = expert.discover_groups(self.equipments, self.config)

        self.print_summary()
        return self.groups

    def run_random_grouping(self) -> List[Dict[str, Any]]:
        """Run pure random grouping."""
        print("\n" + "=" * 60)
        print("🚀 RuneMaster: Random Pipeline (Random Expert)")
        print("=" * 60)

        expert = self.experts["random"]
        self.groups = expert.discover_groups(self.equipments, self.config)

        self.print_summary()
        return self.groups

        """Run genetic grouping with the canonical result and summary contract."""
        print("\n" + "=" * 60)
        print("RuneMaster: Genetic Pipeline (Genetic Expert)")
        print("=" * 60)

        expert = self.experts["genetic"]
        self.groups = expert.discover_groups(self.equipments, self.config)

        self.print_summary()
        return self.groups

    def run_hybrid_grouping(self) -> List[Dict[str, Any]]:
        """Run hybrid grouping: deterministic supplemented by random."""
        print("\n" + "=" * 60)
        print("🚀 RuneMaster: Hybrid Pipeline (Deterministic + Random)")
        print("=" * 60)

        # 1. Deterministic
        det_groups = self.experts["deterministic"].discover_groups(
            self.equipments, self.config
        )

        # 2. Check if random supplement needed
        min_threshold = max(5, int(self.config.random_group_count * 0.5))
        if len(det_groups) < min_threshold:
            print(f"      Supplementing with random groups (count < {min_threshold})")
            rand_groups = self.experts["random"].discover_groups(
                self.equipments, self.config
            )
        else:
            print(
                f"      Deterministic groups sufficient ({len(det_groups)}). Skipping random."
            )
            rand_groups = []

        self.groups = det_groups + rand_groups
        self.print_summary()
        return self.groups

    def run_committee(self) -> List[Dict[str, Any]]:
        """Run the Mixture of Experts committee (MoE).

        Each expert contributes its best discoveries, and the gating network
        evaluates and selects the final ensemble.
        """
        print("\n" + "=" * 60)
        print("🚀 RuneMaster: Mixture of Experts Committee")
        print("=" * 60)

        self.expert_failures = {}

        # Pre-compute graph once for all experts
        shared_graph, shared_resources = GraphBuilder.build_equipment_graph(
            self.equipments,
            min_shared_ratio=self.config.graph_min_shared_ratio,
            min_shared_count=self.config.graph_min_shared_count,
            min_component_size=self.config.graph_min_component_size,
        )

        all_potential_groups = []

        # 1. Dispatch to all experts
        for expert_name, expert in self.experts.items():
            print(f"\n[Expert: {expert_name}] Analyzing equipment pool...")
            try:
                expert_groups = expert.discover_groups(
                    self.equipments,
                    self.config,
                    precomputed_graph=shared_graph,
                    precomputed_resources=shared_resources,
                )
            except (IndexError, KeyError, RuntimeError, TypeError, ValueError) as error:
                message = f"{type(error).__name__}: {error}"
                self.expert_failures[expert_name] = message
                print(f"      ❌ {expert_name} failed: {message}")
                continue

            # Evaluate each group using the expert's fitness function
            for group in expert_groups:
                candidate = GroupCandidate(
                    group["equipments"], self.config.excluded_resource_ids
                )
                group["fitness_score"] = self.objective.score(candidate)
                all_potential_groups.append(group)

        # 2. Select the final non-duplicated portfolio.
        print("\n[Gating Network] Evaluating ensemble and de-duplicating...")
        self.groups = PortfolioSelector.select(
            all_potential_groups, self.config.dedup_overlap_threshold
        )

        print(f"\n      Committee gathered {len(all_potential_groups)} proposals.")
        print(f"      Final ensemble: {len(self.groups)} unique groups selected.")
        if self.expert_failures:
            print(f"      Expert failures: {self.expert_failures}")

        self.print_summary()
        return self.groups

    def get_expert_report(self) -> Dict[str, Any]:
        """Return proposal and failure information from the last committee run."""
        return {
            "failed_experts": dict(self.expert_failures),
            "selected_groups": len(self.groups),
        }

    def get_grouping_method(self) -> str:
        """Get the active grouping method."""
        return self.config.grouping_method

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of processing results."""
        return ProcessingReporter(
            self.groups,
            len(self.equipments),
            self.config.portfolio_quality_weights,
        ).summary()

    def print_summary(self) -> None:
        """Print processing summary."""
        ProcessingReporter(
            self.groups,
            len(self.equipments),
            self.config.portfolio_quality_weights,
        ).print_summary()
