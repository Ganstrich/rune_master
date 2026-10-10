"""RuneMaster: Main orchestrator for equipment group processing pipeline.

This is the central hub that coordinates different GroupingExperts
as a Mixture of Experts (MoE) committee.
"""

from typing import Any, Dict, List, Optional, Tuple

from models import Equipment
from processing.config_dataclass import ProcessingConfig
from processing.experts.graph_expert import GraphGroupingExpert
from processing.experts.random_expert import RandomGroupingExpert
from processing.experts.greedy_expert import GreedyGroupingExpert
from processing.equipment_filter import SetExclusionFilter
from processing.graph_builder import GraphBuilder
from processing.policy import GroupAcceptancePolicy
from processing.selection import ProcessingReporter
from processing.valuation.objective import GroupCandidate
from processing.valuation.overlap import OverlapObjective


def _build_shared_graph(
    equipments: List[Equipment], config: ProcessingConfig
) -> Tuple[Any, Dict[int, set]]:
    """Build the equipment graph shared by all committee experts."""
    return GraphBuilder.build_equipment_graph(
        equipments,
        min_shared_ratio=config.graph_min_shared_ratio,
        min_shared_count=config.graph_min_shared_count,
        min_component_size=config.graph_min_component_size,
        same_set_edge_discount=config.same_set_edge_discount,
    )


def _dispatch_experts(
    experts: Dict[str, Any],
    equipments: List[Equipment],
    config: ProcessingConfig,
    shared_graph: Any,
    shared_resources: Dict[int, set],
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Run all experts with shared graph, collect proposals and failures."""
    all_groups: List[Dict[str, Any]] = []
    failures: Dict[str, str] = {}
    for expert_name, expert in experts.items():
        print(f"\n[Expert: {expert_name}] Analyzing equipment pool...")
        try:
            groups = expert.discover_groups(
                equipments, config,
                precomputed_graph=shared_graph,
                precomputed_resources=shared_resources,
            )
        except (IndexError, KeyError, RuntimeError, TypeError, ValueError) as error:
            message = f"{type(error).__name__}: {error}"
            failures[expert_name] = message
            print(f"      ❌ {expert_name} failed: {message}")
            continue
        all_groups.extend(groups)
        print(f"      ✓ {expert_name}: {len(groups)} proposals")
    return all_groups, failures


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

        # Constraint C2 (metrics-revision §3.8): groups must not be built from
        # panoplie items. Applied once here so every run_* path sees the same
        # pool. The exclusion is reported (metric N10) so it cannot later read
        # as a coverage regression.
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
        # Active experts only (see plans/phase1-decision.md for the removed
        # methods).
        self.experts = {
            "deterministic": GraphGroupingExpert(
                cache_manager, api_client, self.objective, self.policy
            ),
            "random": RandomGroupingExpert(
                cache_manager, api_client, self.objective, self.policy
            ),
            "greedy": GreedyGroupingExpert(
                cache_manager, api_client, self.objective, self.policy
            ),
        }

        # Results
        self.groups: List[Dict[str, Any]] = []
        self.expert_failures: Dict[str, str] = {}

    def run_all(self) -> List[Dict[str, Any]]:
        """Run the default pipeline (backward compatibility)."""
        return self.run_deterministic()

    def run_greedy(self) -> List[Dict[str, Any]]:
        """Run greedy objective-driven grouping."""
        print("\n" + "=" * 60)
        print("🚀 RuneMaster: Greedy Pipeline (Greedy Expert)")
        print("=" * 60)

        self.groups = self.experts["greedy"].discover_groups(self.equipments, self.config)
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

    def run_survey(self) -> List[Dict[str, Any]]:
        """Run every expert and keep the union, tagging each group's origin."""
        print("\n" + "=" * 60)
        print("🚀 RuneMaster: Survey (all experts, union of proposals)")
        print("=" * 60)

        self.expert_failures = {}
        shared_graph, shared_resources = _build_shared_graph(self.equipments, self.config)

        all_groups, self.expert_failures = _dispatch_experts(
            self.experts, self.equipments, self.config, shared_graph, shared_resources
        )

        merged: Dict[frozenset, Dict[str, Any]] = {}
        for group in all_groups:
            fingerprint = frozenset(item.ankama_id for item in group.get("equipments", []))
            if not fingerprint:
                continue
            existing = merged.get(fingerprint)
            if existing is None:
                group["origins"] = [group.get("expert_name", "unknown")]
                merged[fingerprint] = group
            else:
                name = group.get("expert_name", "unknown")
                if name not in existing["origins"]:
                    existing["origins"].append(name)

        groups = sorted(merged.values(), key=lambda g: g.get("quality_score", 0.0), reverse=True)
        for group in groups:
            group["origin"] = "+".join(group["origins"])

        shared = sum(1 for group in groups if len(group["origins"]) > 1)
        print(f"\n[Survey] {len(groups)} distinct groups, {shared} found by more than one expert")
        self.groups = groups
        self.print_summary()
        return self.groups

    def get_expert_report(self) -> Dict[str, Any]:
        """Return proposal and failure information from the last survey run."""
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
