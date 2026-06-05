"""Community detection module using Louvain and BiLouvain algorithms.

This module handles detection of equipment communities (groups) using modularity
optimization and bipartite-aware algorithms.
"""

from itertools import combinations
from typing import Dict, List, Optional, Set, Tuple

import community
import networkx as nx
import numpy as np
import networkx as nx
import community
from itertools import combinations


class CommunityDetector:
    """Detect communities in equipment graphs using various algorithms."""

    @staticmethod
    def calculate_average_pairwise_similarity(
        partition: Dict[int, int],
        equipment_resources: Dict[int, Set[int]],
        _cache: Optional[Dict[Tuple[int, int], float]] = None,
    ) -> float:
        """Calculate average pairwise Jaccard similarity within communities.

        For each community, calculates average similarity between all pairs.
        Returns overall average across all communities.

        Args:
            partition: Dict mapping equipment_id -> community_id
            equipment_resources: Dict from GraphBuilder.get_equipment_resources()
            _cache: Optional dictionary to cache Jaccard results for pairs.

        Returns:
            Average pairwise similarity (0.0 to 1.0)
        """
        # Group nodes by community
        communities_dict = {}
        for equipment, comm_id in partition.items():
            communities_dict.setdefault(comm_id, []).append(equipment)

        total_similarity = 0.0
        total_communities = 0

        for comm_id, equipment_list in communities_dict.items():
            # Filter to equipment with known resources
            valid_equipment = [
                eq for eq in equipment_list
                if eq in equipment_resources
            ]

            if len(valid_equipment) < 2:
                continue

            # Calculate average pairwise similarity for this community
            community_similarity = 0.0
            pair_count = 0

            for i in range(len(valid_equipment)):
                for j in range(i + 1, len(valid_equipment)):
                    eq1 = valid_equipment[i]
                    eq2 = valid_equipment[j]
                    
                    key = (min(eq1, eq2), max(eq1, eq2))
                    if _cache is not None and key in _cache:
                        similarity = _cache[key]
                    else:
                        set1 = equipment_resources[eq1]
                        set2 = equipment_resources[eq2]

                        intersection = len(set1 & set2)
                        union = len(set1 | set2)

                        similarity = intersection / union if union > 0 else 0.0
                        
                        if _cache is not None:
                            _cache[key] = similarity

                    community_similarity += similarity
                    pair_count += 1

            if pair_count > 0:
                total_similarity += (community_similarity / pair_count)
                total_communities += 1

        if total_communities == 0:
            return 0.0

        return total_similarity / total_communities

    @staticmethod
    def calculate_bulk_efficiency(
        partition: Dict[int, int],
        equipment_resources: Dict[int, Set[int]]
    ) -> float:
        """Calculate average bulk acquisition efficiency across communities.

        Efficiency = (shared_resources / total_unique_resources) for each community.
        Returns average across all multi-equipment communities.

        Args:
            partition: Dict mapping equipment_id -> community_id
            equipment_resources: Dict from GraphBuilder.get_equipment_resources()

        Returns:
            Average efficiency (0.0 to 1.0)
        """
        communities_dict = {}
        for equipment, comm_id in partition.items():
            communities_dict.setdefault(comm_id, []).append(equipment)

        total_efficiency = 0.0
        community_count = 0

        for comm_id, equipment_list in communities_dict.items():
            if len(equipment_list) < 2:
                continue

            # Calculate resource overlap
            try:
                all_resources = [
                    equipment_resources[eq] for eq in equipment_list
                ]
            except KeyError:
                # Some equipment may not have resources
                continue

            shared_resources = set.intersection(*all_resources)
            total_unique_resources = set.union(*all_resources)

            if len(total_unique_resources) > 0:
                efficiency = len(shared_resources) / len(total_unique_resources)
                total_efficiency += efficiency
                community_count += 1

        return (total_efficiency / community_count) if community_count > 0 else 0.0

    @staticmethod
    def find_best_louvain_partition(
        equipment_graph: nx.Graph,
        equipment_resources: Dict[int, Set[int]],
        resolution_range: tuple = (1, 10, 1)
    ) -> Dict[int, int]:
        """Find best Louvain partition using modularity optimization.

        Tries multiple resolutions and selects based on average pairwise similarity.

        Args:
            equipment_graph: NetworkX graph from GraphBuilder
            equipment_resources: Equipment-to-resources mapping
            resolution_range: Tuple of (start, stop, step) for resolution values

        Returns:
            Dict mapping equipment_id -> community_id
        """
        best_partition = None
        best_score = -1
        best_resolution = 1.0

        start, stop, step = resolution_range
        if start is None or stop is None or step is None:
            return {}
        
        jaccard_cache: Dict[Tuple[int, int], float] = {}
        for resolution in np.arange(start, stop, step):
            partition = community.best_partition(
                equipment_graph,
                resolution=resolution,
                randomize=True
            )

            # Score based on average pairwise similarity
            pairwise_similarity = (
                CommunityDetector.calculate_average_pairwise_similarity(
                    partition, equipment_resources, _cache=jaccard_cache
                )
            )

            if pairwise_similarity > best_score:
                best_score = pairwise_similarity
                best_partition = partition
                best_resolution = resolution

        print(f"✓ Louvain optimal resolution: {best_resolution:.2f}, "
              f"Score: {best_score:.3f}")

        return best_partition

    @staticmethod
    def find_best_bilouvain_partition(
        equipment_graph: nx.Graph,
        resolution_range: tuple = (1, 10, 1)
    ) -> Dict[int, int]:
        """Find best partition using BiLouvain for bipartite graphs.

        Applies Louvain to bipartite graph and extends partition to all nodes.

        Args:
            equipment_graph: Bipartite NetworkX graph
            resolution_range: Tuple of (start, stop, step)

        Returns:
            Dict mapping node_id -> community_id for all nodes
        """
        # Identify bipartite nodes
        equipment_nodes = [
            n for n in equipment_graph.nodes()
            if equipment_graph.nodes[n].get('bipartite') == 0
        ]
        resource_nodes = [
            n for n in equipment_graph.nodes()
            if equipment_graph.nodes[n].get('bipartite') == 1
        ]

        # Get equipment resources for scoring
        equipment_resources = {}
        for eq in equipment_nodes:
            equipment_resources[eq] = set(equipment_graph.neighbors(eq))

        # Project bipartite graph to equipment nodes
        if equipment_nodes:
            equipment_projection = nx.bipartite.weighted_projected_graph(
                equipment_graph,
                equipment_nodes
            )

            # Apply Louvain on projection
            partition = CommunityDetector.find_best_louvain_partition(
                equipment_projection,
                equipment_resources,
                resolution_range
            )
        else:
            partition = {}

        # Extend partition to resources
        resource_partition = {}
        for resource in resource_nodes:
            connected_equipments = list(equipment_graph.neighbors(resource))
            if connected_equipments:
                # Assign resource to most common group among its neighbors
                groups = [partition.get(eq, -1) for eq in connected_equipments]
                groups = [g for g in groups if g >= 0]
                if groups:
                    most_common_group = max(set(groups), key=groups.count)
                    resource_partition[resource] = most_common_group
                else:
                    resource_partition[resource] = -1
            else:
                resource_partition[resource] = -1

        # Merge partitions
        full_partition = {**partition, **resource_partition}

        print(f"✓ BiLouvain partition complete: "
              f"{len(partition)} equipment, {len(resource_partition)} resources")

        return full_partition

    @staticmethod
    def partition_to_communities(partition: Dict[int, int]) -> Dict[int, List[int]]:
        """Convert partition mapping to communities dict.

        Args:
            partition: Dict mapping node -> community_id

        Returns:
            Dict mapping community_id -> list of node_ids
        """
        communities = {}
        for node, community_id in partition.items():
            communities.setdefault(community_id, []).append(node)
        return communities
