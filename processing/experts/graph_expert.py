"""Graph-based grouping expert using Louvain community detection."""
from typing import List, Dict, Any, Optional, Set
import networkx as nx
from models import Equipment
from processing.experts.base import GroupingExpert
from processing.config_dataclass import ProcessingConfig
from processing.graph_builder import GraphBuilder
from processing.community_detector import CommunityDetector
from processing.group_mapper import GroupMapper

class GraphGroupingExpert(GroupingExpert):
    """Expert that uses graph theory and community detection to find groups.
    
    Optimizes for modularity and natural clusters in the shared-resource network.
    """
    
    def __init__(
        self, 
        cache_manager: Optional[Any] = None,
        api_client: Optional[Any] = None
    ):
        super().__init__("GraphExpert", cache_manager, api_client)

    def discover_groups(
        self, 
        equipments: List[Equipment], 
        config: ProcessingConfig,
        precomputed_graph: Optional[nx.Graph] = None,
        precomputed_resources: Optional[Dict[int, Set[int]]] = None,
    ) -> List[Dict[str, Any]]:
        """Run the graph-based discovery pipeline."""
        print(f"      [{self.name}] Building graph and detecting communities...")
        
        # 1. Build graph
        if precomputed_graph is not None and precomputed_resources is not None:
            graph = precomputed_graph
            resources = precomputed_resources
        else:
            graph, resources = GraphBuilder.build_equipment_graph(
                equipments,
                min_shared_ratio=config.graph_min_shared_ratio,
                min_shared_count=config.group_min_shared_resources, # NEW: Support absolute count
                min_component_size=config.graph_min_component_size,
            )
        
        if graph.number_of_nodes() == 0:
            return []

        # 2. Detect communities
        if config.algorithm == "louvain":
            partition = CommunityDetector.find_best_louvain_partition(
                graph,
                resources,
                resolution_range=config.resolution_range,
            )
        elif config.algorithm == "bilouvain":
            partition = CommunityDetector.find_best_bilouvain_partition(
                graph,
                resolution_range=config.resolution_range,
            )
        else:
            # Fallback to connected components
            components = nx.connected_components(graph)
            partition = {}
            for i, component in enumerate(components):
                for node in component:
                    partition[node] = i
        
        communities = CommunityDetector.partition_to_communities(partition)
        
        # 3. Map to groups
        mapper = GroupMapper(
            equipments,
            excluded_resource_ids=config.excluded_resource_ids
        )
        
        if config.use_inclusive_mapping:
            groups = mapper.map_communities_inclusive(
                communities,
                min_group_size=config.group_min_size,
                max_group_size=config.group_max_size,
                min_shared_resources=config.group_min_shared_resources,
                efficiency_threshold=config.group_efficiency_threshold,
                cache_manager=self.cache_manager,
                api_client=self.api_client,
            )
        else:
            groups = mapper.map_communities(
                communities,
                min_group_size=config.group_min_size,
                max_group_size=config.group_max_size,
                min_shared_resources=config.group_min_shared_resources,
                efficiency_threshold=config.group_efficiency_threshold,
                cache_manager=self.cache_manager,
                api_client=self.api_client,
            )
            
        # Add metadata
        for group in groups:
            group["selection_method"] = "deterministic"
            group["expert_name"] = self.name
            
        return groups
