"""RuneMaster: Main orchestrator for equipment group processing pipeline.

This is the central hub that coordinates:
- Graph building
- Community detection
- Group mapping
- Resource optimization
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from models import Equipment
from processing.graph_builder import GraphBuilder
from processing.community_detector import CommunityDetector
from processing.group_mapper import GroupMapper
import networkx as nx


@dataclass
class ProcessingConfig:
    """Configuration for RuneMaster processing pipeline."""

    # Graph building
    graph_min_shared_ratio: float = 0.2
    graph_min_component_size: int = 2

    # Community detection
    algorithm: str = "louvain"  # "louvain", "bilouvain", or "none"
    resolution_range: tuple = (1, 10, 1)

    # Group mapping
    group_min_size: int = 2
    group_max_size: int = 18
    group_min_shared_resources: int = 2
    group_efficiency_threshold: float = 0.15
    use_inclusive_mapping: bool = False

    # Optimization
    use_resource_optimizer: bool = True

    # Excluded resources (won't count toward sharing efficiency)
    excluded_resource_ids: set = None

    def __post_init__(self):
        """Initialize default values."""
        if self.excluded_resource_ids is None:
            self.excluded_resource_ids = set()


class RuneMaster:
    """Orchestrator for equipment group discovery and optimization.

    Coordinates the complete pipeline:
        Equipment → Graph → Communities → Groups → Visualization
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

        # Processing results
        self.equipment_graph: Optional[nx.Graph] = None
        self.equipment_resources: Optional[Dict] = None
        self.partition: Optional[Dict] = None
        self.communities: Optional[Dict] = None
        self.groups: Optional[List[Dict]] = None

    def run_all(self) -> List[Dict[str, Any]]:
        """Run complete processing pipeline.

        Pipeline:
            1. Build equipment graph
            2. Detect communities
            3. Map to groups
            4. (Optional) Optimize groups

        Returns:
            List of equipment groups with ingredients and efficiency metrics
            
        Note: Equipment stat weights are calculated during loading (EquipmentLoader)
        """
        print("\n" + "="*60)
        print("🚀 RuneMaster: Starting Processing Pipeline")
        print("="*60)

        # Step 1: Build graph
        self.build_graph()

        # Step 2: Detect communities
        self.detect_communities()

        # Step 3: Map to groups
        self.map_groups()

        # Step 4: Optimize (optional)
        if self.config.use_resource_optimizer:
            self.optimize_groups()

        print("\n" + "="*60)
        print(f"✅ Pipeline Complete: {len(self.groups)} groups generated")
        print("="*60 + "\n")

        return self.groups

    def build_graph(self) -> tuple:
        """Step 1: Build equipment similarity graph.

        Creates bipartite graph and Jaccard similarity network.

        Returns:
            Tuple of (equipment_graph, equipment_resources)
        """
        print("\n[1/4] 📊 Building Equipment Graph...")
        print(f"      Input: {len(self.equipments)} equipments")

        self.equipment_graph, self.equipment_resources = GraphBuilder.build_equipment_graph(
            self.equipments,
            min_shared_ratio=self.config.graph_min_shared_ratio,
            min_component_size=self.config.graph_min_component_size,
        )

        print(f"      Output: {self.equipment_graph.number_of_nodes()} nodes, "
              f"{self.equipment_graph.number_of_edges()} edges")

        return self.equipment_graph, self.equipment_resources

    def detect_communities(self) -> Dict[int, int]:
        """Step 2: Detect communities using selected algorithm.

        Supports:
        - "louvain": Standard modularity optimization
        - "bilouvain": Bipartite-aware modularity
        - "none": Skip detection (use connected components)

        Returns:
            Dict mapping node_id -> community_id
        """
        if self.equipment_graph is None or self.equipment_graph.number_of_nodes() == 0:
            print("\n[2/4] ⚠️  No nodes to detect communities from")
            self.partition = {}
            self.communities = {}
            return self.partition

        print(f"\n[2/4] 🔍 Detecting Communities ({self.config.algorithm})...")

        if self.config.algorithm == "louvain":
            self.partition = CommunityDetector.find_best_louvain_partition(
                self.equipment_graph,
                self.equipment_resources,
                resolution_range=self.config.resolution_range,
            )
        elif self.config.algorithm == "bilouvain":
            self.partition = CommunityDetector.find_best_bilouvain_partition(
                self.equipment_graph,
                resolution_range=self.config.resolution_range,
            )
        elif self.config.algorithm == "none":
            # Use connected components as communities
            components = nx.connected_components(self.equipment_graph)
            self.partition = {}
            for i, component in enumerate(components):
                for node in component:
                    self.partition[node] = i
            print(f"      Using connected components: {len(set(self.partition.values()))} communities")
        else:
            raise ValueError(f"Unknown algorithm: {self.config.algorithm}")

        self.communities = CommunityDetector.partition_to_communities(self.partition)
        print(f"      Output: {len(self.communities)} communities")

        return self.partition

    def map_groups(self) -> List[Dict[str, Any]]:
        """Step 3: Map communities to equipment groups.

        Applies filtering based on:
        - Group size (min/max)
        - Shared resources count
        - Efficiency threshold

        Returns:
            List of equipment groups
        """
        print("\n[3/4] 🔗 Mapping Communities to Groups...")

        mapper = GroupMapper(
            self.equipments,
            excluded_resource_ids=self.config.excluded_resource_ids
        )

        if self.config.use_inclusive_mapping:
            self.groups = mapper.map_communities_inclusive(
                self.communities,
                min_group_size=self.config.group_min_size,
                max_group_size=self.config.group_max_size,
                min_shared_resources=self.config.group_min_shared_resources,
                efficiency_threshold=self.config.group_efficiency_threshold,
                cache_manager=self.cache_manager,
                api_client=self.api_client,
            )
        else:
            self.groups = mapper.map_communities(
                self.communities,
                min_group_size=self.config.group_min_size,
                max_group_size=self.config.group_max_size,
                min_shared_resources=self.config.group_min_shared_resources,
                efficiency_threshold=self.config.group_efficiency_threshold,
                cache_manager=self.cache_manager,
                api_client=self.api_client,
            )

        print(f"      Output: {len(self.groups)} valid groups")

        return self.groups

    def optimize_groups(self) -> List[Dict[str, Any]]:
        """Step 4: Optimize groups for bulk acquisition.

        (Currently placeholder - can be extended with ResourceOptimizer)

        Returns:
            Optimized list of groups
        """
        print("\n[4/4] ⚡ Optimizing Groups...")
        print(f"      Input: {len(self.groups)} groups")

        # TODO: Integrate ResourceOptimizer if needed
        # For now, groups are already optimized by GroupMapper

        print(f"      Output: {len(self.groups)} optimized groups")

        return self.groups

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of processing results.

        Returns:
            Dict with pipeline statistics and metrics
        """
        if not self.groups:
            return {}

        total_equipment_in_groups = sum(
            len(g["equipments"]) for g in self.groups
        )
        total_efficiency = sum(
            g["sharing_efficiency"] for g in self.groups
        ) / len(self.groups) if self.groups else 0

        return {
            "total_groups": len(self.groups),
            "total_equipment_in_groups": total_equipment_in_groups,
            "total_equipment": len(self.equipments),
            "retention_rate": total_equipment_in_groups / len(self.equipments) if self.equipments else 0,
            "average_efficiency": total_efficiency,
            "max_efficiency": max((g["sharing_efficiency"] for g in self.groups), default=0),
            "min_efficiency": min((g["sharing_efficiency"] for g in self.groups), default=0),
            "average_group_size": total_equipment_in_groups / len(self.groups) if self.groups else 0,
        }

    def print_summary(self) -> None:
        """Print processing summary."""
        summary = self.get_summary()

        if not summary:
            print("No groups generated")
            return

        print("\n" + "="*60)
        print("📈 PROCESSING SUMMARY")
        print("="*60)
        print(f"Total Groups:           {summary['total_groups']}")
        print(f"Total Equipment:        {summary['total_equipment']}")
        print(f"Equipment in Groups:    {summary['total_equipment_in_groups']}")
        print(f"Retention Rate:         {summary['retention_rate']:.1%}")
        print(f"Avg Group Size:         {summary['average_group_size']:.1f}")
        print(f"Average Efficiency:     {summary['average_efficiency']:.1%}")
        print(f"Efficiency Range:       {summary['min_efficiency']:.1%} - {summary['max_efficiency']:.1%}")
        print("="*60 + "\n")
