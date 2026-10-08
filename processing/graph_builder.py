"""Graph building module for equipment relationship analysis.

This module handles the construction of bipartite graphs and similarity networks
from equipment and resource data.
"""

from itertools import combinations
from typing import Dict, List, Set, Tuple

import networkx as nx

from models import Equipment
from processing.blocks.similarity import jaccard


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
            n
            for n, attr in bipartite_graph.nodes(data=True)
            if attr.get("bipartite") == 0
        }

        for equip in equipment_nodes:
            equipment_resources[equip] = set(bipartite_graph.neighbors(equip))

        return equipment_resources

    @staticmethod
    def _build_inverted_index(
        equipment_resources: Dict[int, Set[int]],
    ) -> Dict[int, Set[int]]:
        """Build inverted index: resource_id -> set of equipment_ids."""
        index: Dict[int, Set[int]] = {}
        for eq_id, resources in equipment_resources.items():
            for rid in resources:
                index.setdefault(rid, set()).add(eq_id)
        return index

    @staticmethod
    def _candidate_pairs_from_index(
        inverted_index: Dict[int, Set[int]],
    ) -> Set[Tuple[int, int]]:
        """Generate candidate equipment pairs that share at least one resource."""
        candidates: Set[Tuple[int, int]] = set()
        for equip_set in inverted_index.values():
            if len(equip_set) < 2:
                continue
            for eq1, eq2 in combinations(sorted(equip_set), 2):
                candidates.add((eq1, eq2))
        return candidates

    @staticmethod
    def create_jaccard_similarity_graph(
        equipment_resources: Dict[int, Set[int]],
        equipment_nodes: Set[int],
        min_shared_ratio: float = 0.2,
        min_shared_count: int = 1,
        equipment_sets: Dict[int, int] | None = None,
        same_set_edge_discount: float = 1.0,
    ) -> nx.Graph:
        """Create equipment similarity graph using Jaccard index or absolute count.

        Jaccard similarity = shared_resources / total_unique_resources

        Args:
            equipment_resources: Dict from get_equipment_resources()
            equipment_nodes: Set of equipment IDs
            min_shared_ratio: Minimum Jaccard similarity to create edge (0.0-1.0)
            min_shared_count: Minimum absolute number of shared resources to create edge
            equipment_sets: Mapping of equipment ID to its set (panoplie) ID
            same_set_edge_discount: Weight multiplier for edges inside one panoplie

        Returns:
            NetworkX graph where edges connect similar equipment
            Edge weight is the Jaccard similarity ratio
        """
        G = nx.Graph()
        G.add_nodes_from(equipment_nodes)
        sets = equipment_sets or {}

        # Build inverted index to find candidate pairs efficiently
        inverted_index = GraphBuilder._build_inverted_index(equipment_resources)
        candidate_pairs = GraphBuilder._candidate_pairs_from_index(inverted_index)

        for eq1, eq2 in candidate_pairs:
            resources1 = equipment_resources[eq1]
            resources2 = equipment_resources[eq2]

            if resources1 and resources2:
                shared = len(resources1 & resources2)
                sharing_ratio = jaccard(resources1, resources2)

                # Connect if they meet BOTH the ratio AND the absolute shared count
                # This prevents weak edges from high-count-low-ratio pairs that would
                # add noise to community detection.
                if sharing_ratio >= min_shared_ratio and shared >= min_shared_count:
                    set1 = sets.get(eq1)
                    same_set = set1 is not None and set1 == sets.get(eq2)
                    # Panoplie items share resources by design; damping their edges
                    # stops Louvain from rediscovering the set as a community.
                    weight = sharing_ratio * (
                        same_set_edge_discount if same_set else 1.0
                    )
                    G.add_edge(
                        eq1,
                        eq2,
                        weight=max(
                            weight, 0.01
                        ),  # Ensure non-zero weight for algorithms
                        shared_count=shared,
                        same_set=same_set,
                    )

        return G

    @staticmethod
    def remove_weak_candidates(
        graph: nx.Graph, min_component_size: int = 2
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
            comp for comp in components if len(comp) >= min_component_size
        ]

        if not meaningful_components:
            return nx.Graph()

        meaningful_nodes = set().union(*meaningful_components)
        return graph.subgraph(meaningful_nodes).copy()

    @staticmethod
    def build_equipment_graph(
        equipments: List[Equipment],
        min_shared_ratio: float = 0.2,
        min_shared_count: int = 1,
        min_component_size: int = 2,
        same_set_edge_discount: float = 1.0,
    ) -> Tuple[nx.Graph, Dict[int, Set[int]]]:
        """Build complete equipment similarity graph from equipments.

        Pipeline:
            1. Create bipartite graph (equipment + resources)
            2. Extract equipment-to-resources mapping
            3. Build similarity graph (Jaccard + Absolute)
            4. Remove weak components

        Args:
            equipments: List of Equipment objects
            min_shared_ratio: Threshold for similarity ratio
            min_shared_count: Threshold for absolute shared resources
            min_component_size: Minimum nodes to keep in component
            same_set_edge_discount: Weight multiplier for edges inside one panoplie

        Returns:
            Tuple of (equipment_graph, equipment_resources_mapping)
        """
        # Step 1: Create bipartite graph
        bipartite_graph = GraphBuilder.create_bipartite_graph(equipments)

        # Step 2: Extract mappings
        equipment_nodes = {
            n
            for n, attr in bipartite_graph.nodes(data=True)
            if attr.get("bipartite") == 0
        }
        equipment_resources = GraphBuilder.get_equipment_resources(bipartite_graph)

        # Step 3: Create similarity graph
        equipment_graph = GraphBuilder.create_jaccard_similarity_graph(
            equipment_resources,
            equipment_nodes,
            min_shared_ratio=min_shared_ratio,
            min_shared_count=min_shared_count,
            equipment_sets={
                int(equipment.ankama_id): int(equipment.set_id)
                for equipment in equipments
                if isinstance(getattr(equipment, "set_id", None), int)
            },
            same_set_edge_discount=same_set_edge_discount,
        )

        # Step 4: Remove weak components
        equipment_graph = GraphBuilder.remove_weak_candidates(
            equipment_graph, min_component_size=min_component_size
        )

        # Step 5: Filter equipment_resources to only include nodes that survived
        # component filtering. This ensures consistency between the graph and the
        # resources dict — downstream consumers won't find resource data for
        # equipment that was removed.
        surviving_nodes = set(equipment_graph.nodes())
        equipment_resources = {
            eq_id: resources
            for eq_id, resources in equipment_resources.items()
            if eq_id in surviving_nodes
        }

        return equipment_graph, equipment_resources
