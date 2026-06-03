"""RuneMaster: Main orchestrator for equipment group processing pipeline.

This is the central hub that coordinates different GroupingExperts 
as a Mixture of Experts (MoE) committee.
"""

from typing import Dict, List, Any, Optional
from models import Equipment
from processing.config_dataclass import ProcessingConfig
from processing.experts.graph_expert import GraphGroupingExpert
from processing.experts.random_expert import RandomGroupingExpert
from processing.experts.genetic_expert import GeneticGroupingExpert

class RuneMaster:
    """Orchestrator for equipment group discovery and optimization.

    Acts as a Gating Network that coordinates specialized GroupingExperts.
    """

    def __init__(
        self,
        equipments: List[Equipment],
        config: Optional[ProcessingConfig] = None,
        cache_manager=None,
        api_client=None
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

        # Initialize Experts
        self.experts = {
            "deterministic": GraphGroupingExpert(cache_manager, api_client),
            "random": RandomGroupingExpert(cache_manager, api_client),
            "genetic": GeneticGroupingExpert(cache_manager, api_client),
        }
        
        # Results
        self.groups: List[Dict[str, Any]] = []

    def run_all(self) -> List[Dict[str, Any]]:
        """Run the default pipeline (backward compatibility)."""
        return self.run_deterministic()

    def run_deterministic(self) -> List[Dict[str, Any]]:
        """Run pure graph-based grouping."""
        print("\n" + "="*60)
        print("🚀 RuneMaster: Deterministic Pipeline (Graph Expert)")
        print("="*60)
        
        expert = self.experts["deterministic"]
        self.groups = expert.discover_groups(self.equipments, self.config)
        
        self.print_summary()
        return self.groups

    def run_random_grouping(self) -> List[Dict[str, Any]]:
        """Run pure random grouping."""
        print("\n" + "="*60)
        print("🚀 RuneMaster: Random Pipeline (Random Expert)")
        print("="*60)
        
        expert = self.experts["random"]
        self.groups = expert.discover_groups(self.equipments, self.config)
        
        self.print_summary()
        return self.groups

    def run_hybrid_grouping(self) -> List[Dict[str, Any]]:
        """Run hybrid grouping: deterministic supplemented by random."""
        print("\n" + "="*60)
        print("🚀 RuneMaster: Hybrid Pipeline (Deterministic + Random)")
        print("="*60)

        # 1. Deterministic
        det_groups = self.experts["deterministic"].discover_groups(self.equipments, self.config)
        
        # 2. Check if random supplement needed
        min_threshold = max(5, int(self.config.random_group_count * 0.5))
        if len(det_groups) < min_threshold:
            print(f"      Supplementing with random groups (count < {min_threshold})")
            rand_groups = self.experts["random"].discover_groups(self.equipments, self.config)
        else:
            print(f"      Deterministic groups sufficient ({len(det_groups)}). Skipping random.")
            rand_groups = []

        self.groups = det_groups + rand_groups
        self.print_summary()
        return self.groups

    def run_committee(self) -> List[Dict[str, Any]]:
        """Run the Mixture of Experts committee (MoE).
        
        Each expert contributes its best discoveries, and the gating network
        evaluates and selects the final ensemble.
        """
        print("\n" + "="*60)
        print("🚀 RuneMaster: Mixture of Experts Committee")
        print("="*60)
        
        all_potential_groups = []
        
        # 1. Dispatch to all experts
        for expert_name, expert in self.experts.items():
            print(f"\n[Expert: {expert_name}] Analyzing equipment pool...")
            expert_groups = expert.discover_groups(self.equipments, self.config)
            
            # Evaluate each group using the expert's fitness function
            for group in expert_groups:
                group["fitness_score"] = expert.evaluate_group(group)
                all_potential_groups.append(group)
        
        # 2. Gating Network: Evaluate and De-duplicate
        print("\n[Gating Network] Evaluating ensemble and de-duplicating...")
        
        # Sort by fitness score (descending)
        all_potential_groups.sort(key=lambda x: x.get("fitness_score", 0), reverse=True)
        
        # Simple de-duplication based on equipment IDs set
        unique_groups = []
        seen_equipment_sets = []
        
        for group in all_potential_groups:
            # ENFORCE MINIMUM SIZE (Final Committee Sanity Check)
            if len(group.get("equipments", [])) < 2:
                continue

            equip_ids = sorted([e.ankama_id for e in group["equipments"]])
            if equip_ids not in seen_equipment_sets:
                unique_groups.append(group)
                seen_equipment_sets.append(equip_ids)
        
        self.groups = unique_groups
        
        print(f"\n      Committee gathered {len(all_potential_groups)} proposals.")
        print(f"      Final ensemble: {len(self.groups)} unique groups selected.")
        
        self.print_summary()
        return self.groups

    def get_grouping_method(self) -> str:
        """Get the active grouping method."""
        return self.config.grouping_method

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of processing results."""
        if not self.groups:
            return {}

        total_equipment_in_groups = sum(
            len(g["equipments"]) for g in self.groups
        )
        total_efficiency = sum(
            g["sharing_efficiency"] for g in self.groups
        ) / len(self.groups) if self.groups else 0

        group_sizes = [len(g["equipments"]) for g in self.groups]

        return {
            "total_groups": len(self.groups),
            "total_equipment_in_groups": total_equipment_in_groups,
            "total_equipment": len(self.equipments),
            "retention_rate": total_equipment_in_groups / len(self.equipments) if self.equipments else 0,
            "average_efficiency": total_efficiency,
            "max_efficiency": max((g["sharing_efficiency"] for g in self.groups), default=0),
            "min_efficiency": min((g["sharing_efficiency"] for g in self.groups), default=0),
            "average_group_size": total_equipment_in_groups / len(self.groups) if self.groups else 0,
            "max_group_size": max(group_sizes, default=0),
        }

    def print_summary(self) -> None:
        """Print processing summary."""
        summary = self.get_summary()

        if not summary:
            print("No groups generated")
            return

        print("\n" + "="*60)
        print("📈 COMMITTEE SUMMARY")
        print("="*60)
        print(f"Total Groups:           {summary['total_groups']}")
        print(f"Total Equipment:        {summary['total_equipment']}")
        print(f"Equipment in Groups:    {summary['total_equipment_in_groups']}")
        print(f"Retention Rate:         {summary['retention_rate']:.1%}")
        print(f"Avg Group Size:         {summary['average_group_size']:.1f}")
        print(f"Average Efficiency:     {summary['average_efficiency']:.1%}")
        print(f"Efficiency Range:       {summary['min_efficiency']:.1%} - {summary['max_efficiency']:.1%}")
        print("="*60 + "\n")
