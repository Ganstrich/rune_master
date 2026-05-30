"""Graph building module for equipment relationship analysis.

This module handles the construction of bipartite graphs and similarity networks
from equipment and resource data.
"""

from itertools import combinations
from typing import Dict, Set, List, Tuple
import networkx as nx
from models import Equipment


class GraphBuilder:
    """Build graphs for equipment-resource relationships."""

    @staticmethod
    def create_bipartite_graph(equipments: List[Equipment]) -> nx.Graph:
        """Create a bipartite graph from equipment list.

        Equipment nodes have bipartite=0, resource nodes have bipartite=1.
        Edges connect equipment -> resource based on recipes.

        Args:
            equipments: List of Equipment dataclass objects

        Returns:
            NetworkX bipartite graph with equipment and resource nodes
        """
        B = nx.Graph()
        
        for equip in equipments:
            # Add equipment node
            B.add_node(equip.ankama_id, bipartite=0, type="equipment")
            
            # Add resource nodes and edges
            if equip.recipe:
                for resource_req in equip.recipe:
                    resource_id = resource_req.resource_id
                    
                    if not B.has_node(resource_id):
                        B.add_node(resource_id, bipartite=1, type="resource")
                    
                    B.add_edge(equip.ankama_id, resource_id)

        return B

    @staticmethod
    def get_equipment_resources(bipartite_graph: nx.Graph) -> Dict[int, Set[int]]:
        """Extract equipment-to-resources mapping from bipartite graph.

        Args:
            bipartite_graph: NetworkX bipartite graph from create_bipartite_graph()

        Returns:
            Dict mapping equipment_id -> set of resource_ids
        """
        equipment_resources = {}
        equipment_nodes = {
            n for n, attr in bipartite_graph.nodes(data=True)
            if attr.get("bipartite") == 0
        }

        for equip in equipment_nodes:
            equipment_resources[equip] = set(bipartite_graph.neighbors(equip))

        return equipment_resources

    @staticmethod
    def create_jaccard_similarity_graph(
        equipment_resources: Dict[int, Set[int]],
        equipment_nodes: Set[int],
        min_shared_ratio: float = 0.2
    ) -> nx.Graph:
        """Create equipment similarity graph using Jaccard index.

        Jaccard similarity = shared_resources / total_unique_resources

        Args:
            equipment_resources: Dict from get_equipment_resources()
            equipment_nodes: Set of equipment IDs
            min_shared_ratio: Minimum Jaccard similarity to create edge (0.0-1.0)

        Returns:
            NetworkX graph where edges connect similar equipment
            Edge weight is the Jaccard similarity ratio
        """
        G = nx.Graph()
        G.add_nodes_from(equipment_nodes)

        for eq1, eq2 in combinations(equipment_nodes, 2):
            resources1 = equipment_resources[eq1]
            resources2 = equipment_resources[eq2]

            if resources1 and resources2:
                shared = len(resources1 & resources2)
                total_unique = len(resources1 | resources2)
                sharing_ratio = shared / total_unique if total_unique > 0 else 0

                # Only connect if they share a significant portion of resources
                if sharing_ratio >= min_shared_ratio:
                    G.add_edge(
                        eq1, eq2,
                        weight=sharing_ratio,
                        shared_count=shared
                    )

        return G

    @staticmethod
    def remove_weak_candidates(
        graph: nx.Graph,
        min_component_size: int = 2
    ) -> nx.Graph:
        """Remove isolated nodes and small connected components.

        Args:
            graph: NetworkX graph
            min_component_size: Minimum nodes per connected component to keep

        Returns:
            Filtered graph with only meaningful components
        """
        components = list(nx.connected_components(graph))
        meaningful_components = [
            comp for comp in components
            if len(comp) >= min_component_size
        ]

        if not meaningful_components:
            return nx.Graph()

        meaningful_nodes = set().union(*meaningful_components)
        return graph.subgraph(meaningful_nodes).copy()

    @staticmethod
    def build_equipment_graph(
        equipments: List[Equipment],
        min_shared_ratio: float = 0.2,
        min_component_size: int = 2
    ) -> Tuple[nx.Graph, Dict[int, Set[int]]]:
        """Build complete equipment similarity graph from equipments.

        Pipeline:
            1. Create bipartite graph (equipment + resources)
            2. Extract equipment-to-resources mapping
            3. Build Jaccard similarity graph
            4. Remove weak components

        Args:
            equipments: List of Equipment objects
            min_shared_ratio: Threshold for edge creation
            min_component_size: Minimum nodes to keep in component

        Returns:
            Tuple of (equipment_graph, equipment_resources_mapping)
        """
        # Step 1: Create bipartite graph
        bipartite_graph = GraphBuilder.create_bipartite_graph(equipments)

        # Step 2: Extract mappings
        equipment_nodes = {
            n for n, attr in bipartite_graph.nodes(data=True)
            if attr.get("bipartite") == 0
        }
        equipment_resources = GraphBuilder.get_equipment_resources(bipartite_graph)

        # Step 3: Create Jaccard similarity graph
        equipment_graph = GraphBuilder.create_jaccard_similarity_graph(
            equipment_resources,
            equipment_nodes,
            min_shared_ratio=min_shared_ratio
        )

        # Step 4: Remove weak components
        equipment_graph = GraphBuilder.remove_weak_candidates(
            equipment_graph,
            min_component_size=min_component_size
        )

        return equipment_graph, equipment_resources
