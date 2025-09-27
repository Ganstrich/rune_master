from collections import defaultdict
import networkx as nx
from networkx.algorithms import bipartite
import community
from utils import CacheManager
# from cdlib import algorithms
import numpy as np
from itertools import combinations
from tqdm.auto import tqdm
from models import Equipment, Resource, ResourceRequirement
from typing import List, Tuple, Dict, Any


class DataProcessor:
    """DataProcessor class to handle equipment and resource graph processing
    """

    def __init__(self, equipments: List[Equipment] = None, cache_manager=None):
        # Allows injecting a cache manager for testing; default to the
        # project's CacheManager class.
        self.cache = cache_manager or CacheManager
        self.equipments = equipments
        self.excluded_resources_ids = {15263, 14635} # Pépite et Roses des sables
                
    def create_bipartite_graph(self, equipments: List[Equipment]) -> nx.Graph:
        """Create a simple bipartite graph from equipment list.

        Equipment nodes will have attribute bipartite=0 and resource nodes
        bipartite=1. Edges will connect equipment -> resource.
        """
        B = nx.Graph()
        for equip in equipments:            
            # Add equipment node
            B.add_node(equip.ankama_id, bipartite=0, type="equipment")
            
            # Add resource nodes and edges
            for resource in equip.recipe:
                if not B.has_node(resource.resource_id):
                    B.add_node(resource.resource_id, bipartite=1, type="resource")
                B.add_edge(equip.ankama_id, resource.resource_id)

        return B
    
    def get_equipment_resources(self, bipartite_graph:nx.Graph, equipment_nodes) -> Dict[int, set]:
        """Get a mapping of equipment_id -> set of resource_ids"""
        equipment_resources = {}
        for equip in equipment_nodes:
            equipment_resources[equip] = set(bipartite_graph.neighbors(equip))
        return equipment_resources
    
    def create_jaccard_similarity_graph(self, equipment_resources, equipment_nodes, min_shared_ratio=0.2) -> nx.Graph:
        """
        Simple Jaccard similarity graph - perfect for your use case
        """
        G = nx.Graph()
        G.add_nodes_from(equipment_nodes)
        
        for eq1, eq2 in combinations(equipment_nodes, 2):
            resources1 = equipment_resources[eq1]
            resources2 = equipment_resources[eq2]
            
            if resources1 and resources2:
                shared = len(resources1 & resources2)
                total_unique = len(resources1 | resources2)
                sharing_ratio = shared / total_unique
                
                # Only connect if they share a significant portion of resources
                if sharing_ratio >= min_shared_ratio:
                    G.add_edge(eq1, eq2, weight=sharing_ratio, shared_count=shared)
        
        return G
    
    def remove_weak_candidates(self, graph:nx.Graph, min_component_size=2):
        """Remove isolated nodes and very small components"""
        components = list(nx.connected_components(graph))
        meaningful_components = [comp for comp in components if len(comp) >= min_component_size]
        meaningful_nodes = set().union(*meaningful_components)
        return graph.subgraph(meaningful_nodes).copy()
    
    def get_equipement_graph_and_resources(self, min_shared_ratio):
        # Step 1: Create bipartite graph using your method
        bipartite_graph = self.create_bipartite_graph(self.equipments)

        # Step 2: Get equipment nodes
        equipment_nodes = {n for n, attr in bipartite_graph.nodes(data=True) if attr["bipartite"] == 0}
        print(f"Found {len(equipment_nodes)} equipment nodes")
        print(f"Found {len(bipartite_graph.nodes) - len(equipment_nodes)} resource nodes")
        
        # Step 3: Create Jaccard similarity graph
        equipment_resources = self.get_equipment_resources(bipartite_graph, equipment_nodes)
        equipment_graph : nx.Graph = self.create_jaccard_similarity_graph(equipment_resources, equipment_nodes, min_shared_ratio)
        print(f"Jaccard graph: {equipment_graph.number_of_nodes()} nodes, {equipment_graph.number_of_edges()} edges")
        
        # Step 4: Remove singletons
        equipment_graph = self.remove_weak_candidates(equipment_graph, min_component_size=2)
        print(f"After removing weak candidates: {equipment_graph.number_of_nodes()} nodes, {equipment_graph.number_of_edges()} edges")
        
        if equipment_graph.number_of_nodes() == 0:
            print("No meaningful groups found. Try lowering min_shared_ratio.")
            return {}
        return equipment_graph, equipment_resources
    
    def find_best_louvain_partition(self, equipment_graph:nx.Graph, resolution_range=(1, 10, 1), target_community_size=2, equipment_resources=None):
        """
        Find the best partition using modularity optimization
        """
        # Find optimal resolution for target community size
        best_partition = None
        best_score = -1
        best_resolution = 1.0
                
        for resolution in np.arange(resolution_range[0], resolution_range[1], resolution_range[2]):
            partition = community.best_partition(equipment_graph, resolution=resolution, randomize=True)
            
            # Calculate community size distribution
            communities = {}
            for node, comm_id in partition.items():
                communities.setdefault(comm_id, []).append(node)
            
            # Score based on community sizes (penalize too small/large communities)
            size_score = 0
            for comm_id, nodes in communities.items():
                size_diff = abs(len(nodes) - target_community_size)
                # Higher score for communities closer to target size
                size_score += 1 / (1 + size_diff)
                
            if equipment_resources is None:
                equipment_resources = self.get_equipment_resources(equipment_graph, equipment_graph.nodes())
            
            # Also consider resource sharing efficiency
            sharing_score = self.calculate_bulk_efficiency(partition, equipment_resources)
            
            total_score = 0.6 * sharing_score + 0.4 * size_score
            
            if total_score > best_score:
                best_score = total_score
                best_partition = partition
                best_resolution = resolution
        
        print(f"Optimal resolution: {best_resolution:.2f}, Score: {best_score:.3f}")
        return best_partition
    
    def find_best_bilouvain_partition(self, equipment_graph:nx.Graph, resolution=30.0):
        """
        Algorithme BiLouvain adapté pour graphes bipartis
        """
        equipment_nodes = [n for n in equipment_graph.nodes() if equipment_graph.nodes[n].get('bipartite') == 0]
        resource_nodes = [n for n in equipment_graph.nodes() if equipment_graph.nodes[n].get('bipartite') == 1]
        
        # Phase 1: Projection pondérée sur les équipements
        equipment_projection = nx.bipartite.weighted_projected_graph(equipment_graph, equipment_nodes)
        
        # Utiliser Louvain standard sur la projection comme point de départ
            # Utiliser Louvain standard sur la projection comme point de départ
        import community as community_louvain
        partition = community_louvain.best_partition(equipment_projection, 
                                                resolution=resolution, 
                                                )
        
        # Étendre la partition aux ressources (affecter chaque ressource au groupe majoritaire de ses équipements connectés)
        resource_partition = {}
        for resource in resource_nodes:
            connected_equipments = list(equipment_graph.neighbors(resource))
            if connected_equipments:
                # Trouver le groupe le plus fréquent parmi les équipements connectés
                groups = [partition[eq] for eq in connected_equipments]
                most_common_group = max(set(groups), key=groups.count)
                resource_partition[resource] = most_common_group
            else:
                resource_partition[resource] = -1  # Ressource isolée
        
        # Fusionner les partitions
        full_partition = {**partition, **resource_partition}
        
        return full_partition
        
    def find_equipment_groups(self, min_shared_ratio=0.2, resolution_range=(1,10, 1), target_community_size=2):
        """
        Main method to find equipment communities for bulk acquisition
        """

        equipment_graph, equipment_resources = self.get_equipement_graph_and_resources(min_shared_ratio)

        partition = self.find_best_louvain_partition(equipment_graph, resolution_range=resolution_range, target_community_size=target_community_size, equipment_resources=equipment_resources)
        
        
        # Group equipment nodes by community id
        communities = self._partition_to_communities(partition)
        
        groups = self.map_communities(communities, min_group_size=2, max_group_size=18, min_shared_resources=2, efficiency_threshold=0.15)
    
        return groups
    
    def find_bi_louvain_groups(self,resolution=30):
        
        bipartite_graph = self.create_bipartite_graph(self.equipments)
        partition = self.find_best_bilouvain_partition(bipartite_graph, resolution=resolution)
        communities = self._partition_to_communities(partition)
        groups = self.map_communities(communities, min_group_size=2, max_group_size=18, min_shared_resources=2, efficiency_threshold=0.15)
        return groups
    
    def map_communities(self, communities, min_group_size=2, max_group_size=8, min_shared_resources=2, efficiency_threshold=0.3):
        # Map equipment ids back to Equipment dataclass instances
        equipment_dict = {int(e.ankama_id): e for e in self.equipments}
        groups = []
        print(f"Found {len(communities)} communities.")

        for community_id, equip_ids in tqdm(
            communities.items(),
            desc="Processing communities",
            total=len(communities),
            unit="community",
            leave=True,
        ):
            group_equipments = self._resolve_equipment_objects(equip_ids, equipment_dict)

            # Skip if group doesn't meet size requirements
            if not (min_group_size <= len(group_equipments) <= max_group_size):
                continue

            # Calculate shared resources (excluding specified resources)
            shared_count, total_shared, efficiency = self.calculate_shared_resources(
                group_equipments, self.excluded_resources_ids
            )

            # Calculate total ingredients needed for the group
            total_ingredients = self.calculate_total_ingredients(group_equipments)

            # Apply multiple filters
            if shared_count >= min_shared_resources and efficiency >= efficiency_threshold:
                groups.append(
                    {
                        "equipments": group_equipments,
                        "shared_resources_count": shared_count,
                        "total_shared_resources": total_shared,
                        "sharing_efficiency": efficiency,
                        "total_ingredients": total_ingredients,
                        "unique_ingredients_count": len(total_ingredients),
                        "total_items_needed": sum(
                            ingredient["total_quantity"] for ingredient in total_ingredients.values()
                        ),
                    }
                )

        # Sort groups by sharing efficiency (descending)
        groups.sort(key=lambda x: x["sharing_efficiency"], reverse=True)

        return groups
         
    def analyze_communities(self, partition, B):
        """Analyze the resulting communities"""
        communities = {}
        for equipment, comm_id in partition.items():
            communities.setdefault(comm_id, []).append(equipment)
        
        print(f"\n=== COMMUNITY ANALYSIS ===")
        print(f"Found {len(communities)} communities")
        
        results = []
        for comm_id, equipment_list in sorted(communities.items(), key=lambda x: len(x[1]), reverse=True):
            # Calculate resource sharing statistics
            resource_sets = [set(B.neighbors(eq)) for eq in equipment_list]
            shared_resources = set.intersection(*resource_sets) if resource_sets else set()
            total_resources = set.union(*resource_sets) if resource_sets else set()
            
            sharing_ratio = len(shared_resources) / len(total_resources) if total_resources else 0
            
            results.append({
                'community_id': comm_id,
                'equipment_count': len(equipment_list),
                'shared_resources': len(shared_resources),
                'total_resources': len(total_resources),
                'sharing_ratio': sharing_ratio,
                'equipment_list': equipment_list,
                'shared_resource_list': sorted(shared_resources)
            })
            
            print(f"\nCommunity {comm_id}:")
            print(f"  Equipment: {len(equipment_list)} items")
            print(f"  Shared resources: {len(shared_resources)}/{len(total_resources)} ({sharing_ratio:.1%})")
            print(f"  Equipment IDs: {equipment_list}")
            if shared_resources:
                print(f"  Shared resources: {sorted(shared_resources)}")
        
        return results
    
    def calculate_community_acquisition_efficiency(self, partition, B):
        """
        Calculate how efficient bulk acquisition would be for each community
        Higher score = better (more shared ingredients relative to total)
        """
        community_efficiency = {}
        
        # Group equipment by community
        communities = {}
        for equipment, comm_id in partition.items():
            communities.setdefault(comm_id, []).append(equipment)
        
        for comm_id, equipment_list in communities.items():
            if len(equipment_list) < 2:
                continue  # Skip single-equipment communities
            
            # Get all ingredients needed by this community
            all_ingredients = set()
            equipment_ingredient_sets = {}
            
            for equip in equipment_list:
                ingredients = set(B.neighbors(equip))
                equipment_ingredient_sets[equip] = ingredients
                all_ingredients.update(ingredients)
            
            # Calculate efficiency metric
            total_ingredients = len(all_ingredients)
            shared_ingredients = set.intersection(*equipment_ingredient_sets.values())
            total_possible_shared = sum(len(ingredients) for ingredients in equipment_ingredient_sets.values())
            
            # Efficiency = (actually shared) / (total unique in community)
            # Higher = more ingredient overlap, better bulk acquisition
            efficiency = len(shared_ingredients) / total_ingredients if total_ingredients > 0 else 0
            
            community_efficiency[comm_id] = {
                'efficiency': efficiency,
                'shared_ingredients': len(shared_ingredients),
                'total_ingredients': total_ingredients,
                'equipment_count': len(equipment_list)
            }
        
        return community_efficiency

    def calculate_total_ingredients(self, group_equipments):
        """
        Calculate the total ingredients needed for all equipment in the group.
        Returns a dictionary with resource_id as key and aggregated ingredient info as value.
        """
        ingredients = defaultdict(
            lambda: {
                "name": None,
                "total_quantity": 0,
                "used_in_equipments": [],
                "quantity_per_equipment": {},
            }
        )

        for equipment in group_equipments:
            for resource_id, quantity in self._iter_equipment_recipe(equipment):
                resource_id = int(resource_id)
                ingredients[resource_id]["total_quantity"] += int(quantity)
                name = getattr(equipment, "name", None) or str(getattr(equipment, "ankama_id", "?"))
                ingredients[resource_id]["used_in_equipments"].append(name)
                ingredients[resource_id]["quantity_per_equipment"][name] = int(quantity)

                # Get resource name if not already set using CacheManager.get_resource_info
                if ingredients[resource_id]["name"] is None:
                    info = self.cache.get_resource_info(resource_id)
                    ingredients[resource_id]["name"] = info.name if info is not None else self.cache.get_resource_name(resource_id)

        return dict(ingredients)

    def calculate_shared_resources(self, group_equipments, excluded_resource_ids):
        """
        Calculate shared resources for a group, excluding specified resources.
        Returns:
            - Count of shared resources (excluding excluded ones)
            - Total shared resources (including excluded ones)
            - Sharing efficiency (shared_count / total_unique_resources)
        """
        resource_usage = defaultdict(int)
        all_resources = set()

        for equipment in group_equipments:
            for resource_id, _qty in self._iter_equipment_recipe(equipment):
                resource_id = int(resource_id)
                resource_usage[resource_id] += 1
                all_resources.add(resource_id)

        # Calculate shared resources (excluding specified ones)
        shared_resources = {rid: count for rid, count in resource_usage.items() if count > 1 and rid not in excluded_resource_ids}

        # Calculate total shared resources (including excluded ones)
        total_shared_resources = {rid: count for rid, count in resource_usage.items() if count > 1}

        # Calculate sharing efficiency
        total_unique = len(all_resources)
        shared_count = len(shared_resources)
        efficiency = shared_count / total_unique if total_unique > 0 else 0

        return shared_count, len(total_shared_resources), efficiency

    def get_shared_resources(self, group_equipments, excluded_resource_ids):
        """
        Get shared resources for a group, excluding specified resources.
        """
        resource_usage = defaultdict(int)

        for equipment in group_equipments:
            for resource_id, _qty in self._iter_equipment_recipe(equipment):
                resource_usage[int(resource_id)] += 1

        # Return only shared resources that aren't excluded
        return {rid: count for rid, count in resource_usage.items() if count > 1 and rid not in excluded_resource_ids}

    # -----------------
    # Helper utilities
    # -----------------
    def _partition_to_communities(self, partition):
        """Group partition mapping (node -> community) into communities dict."""
        communities = {}
        for node, community_id in partition.items():
            communities.setdefault(community_id, []).append(node)
        return communities

    def _resolve_equipment_objects(self, equip_ids, equipment_dict):
        """Resolve node ids to equipment dict objects, tolerant to str/int node ids."""
        group_equipments = []
        for equip_id in equip_ids:
            if isinstance(equip_id, str):
                try:
                    equip_id_int = int(equip_id)
                    if equip_id_int in equipment_dict:
                        group_equipments.append(equipment_dict[equip_id_int])
                except ValueError:
                    continue
            elif equip_id in equipment_dict:
                group_equipments.append(equipment_dict[equip_id])
        return group_equipments

    def _ensure_equipment_dataclass(self, equip: Any) -> Equipment:
        """Return an Equipment dataclass: if input is dict, try to convert using Equipment.from_raw.
        Falls back to a minimal Equipment construction when necessary.
        """
        if isinstance(equip, Equipment):
            return equip
        if isinstance(equip, dict):
            try:
                return Equipment.from_raw(equip)
            except Exception:
                # Build a minimal Equipment instance if from_raw fails
                reqs = []
                for item in (equip.get("recipe") or []):
                    try:
                        reqs.append(ResourceRequirement(resource_id=int(item.get("item_ankama_id")), quantity=int(item.get("quantity", 1))))
                    except Exception:
                        continue

                return Equipment(
                    ankama_id=int(equip.get("ankama_id")),
                    type=equip.get("type", {}),
                    name=equip.get("name", ""),
                    level=int(equip.get("level", 0)),
                    recipe=reqs,
                    image_urls=equip.get("image_urls"),
                )

        raise TypeError(f"Unsupported equipment type: {type(equip)!r}")

    def _iter_equipment_recipe(self, equipment: Any):
        """Yield (resource_id, quantity) pairs from equipment recipe for either dataclass or raw dict."""
        # Equipment dataclass with ResourceRequirement entries
        if isinstance(equipment, Equipment):
            for req in (equipment.recipe or []):
                if isinstance(req, ResourceRequirement):
                    yield req.resource_id, req.quantity
                elif isinstance(req, dict):
                    try:
                        yield int(req.get("item_ankama_id")), int(req.get("quantity", 1))
                    except Exception:
                        continue
                else:
                    # Try attribute access
                    rid = getattr(req, "resource_id", None) or getattr(req, "item_ankama_id", None)
                    qty = getattr(req, "quantity", 1)
                    if rid is not None:
                        yield int(rid), int(qty)
            return

        # Raw dict format
        for item in (equipment.get("recipe") or []):
            try:
                yield int(item.get("item_ankama_id")), int(item.get("quantity", 1))
            except Exception:
                continue

    def create_enhanced_equipment_graph(self, B, equipment_nodes, min_shared_ratio=0.3):
        """
        Create equipment graph optimized for bulk acquisition
        - Uses Jaccard similarity (shared/total unique resources)
        - Filters weak connections below threshold
        - Ensures meaningful groups by removing isolated nodes
        """
        # Precompute resources for each equipment
        equipment_resources = {}
        for equip in equipment_nodes:
            equipment_resources[equip] = set(B.neighbors(equip))
        
        # Create graph with Jaccard similarity
        G = nx.Graph()
        G.add_nodes_from(equipment_nodes)
        
        # Add edges based on resource sharing ratio
        for eq1, eq2 in combinations(equipment_nodes, 2):
            resources1 = equipment_resources[eq1]
            resources2 = equipment_resources[eq2]
            
            if resources1 and resources2:
                shared = len(resources1 & resources2)
                total_unique = len(resources1 | resources2)
                sharing_ratio = shared / total_unique
                
                # Only connect if they share a significant portion of resources
                if sharing_ratio >= min_shared_ratio:
                    G.add_edge(eq1, eq2, weight=sharing_ratio, shared_count=shared)
        
        return G, equipment_resources

    def calculate_bulk_efficiency(self, partition, equipment_resources):
        """
        Calculate how efficient bulk acquisition would be for these communities
        """
        communities = {}
        for equipment, comm_id in partition.items():
            communities.setdefault(comm_id, []).append(equipment)
        
        total_efficiency = 0
        community_count = 0
        
        for comm_id, equipment_list in communities.items():
            if len(equipment_list) < 2:
                continue
                
            # Calculate resource overlap for this community
            all_resources = [equipment_resources[eq] for eq in equipment_list]
            shared_resources = set.intersection(*all_resources)
            total_unique_resources = set.union(*all_resources)
            
            if len(total_unique_resources) > 0:
                efficiency = len(shared_resources) / len(total_unique_resources)
                total_efficiency += efficiency
                community_count += 1
        
        return total_efficiency / community_count if community_count > 0 else 0