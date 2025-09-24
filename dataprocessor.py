from collections import defaultdict
import networkx as nx
from networkx.algorithms import bipartite
import community
from utils import CacheManager
from cdlib import algorithms
from itertools import combinations
from tqdm.auto import tqdm


class DataProcessor:
    """DataProcessor

    Refactored to use instance methods where appropriate and split
    large functions into smaller helpers for readability and easier
    testing/extension.
    """

    def __init__(self, cache_manager=None):
        # Allows injecting a cache manager for testing; default to the
        # project's CacheManager.
        self.cache = cache_manager or CacheManager

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

# Evaluate your partition
# efficiency_scores = calculate_community_acquisition_efficiency(partition, B)
    
    def create_jaccard_similarity_graph(self, B, equipment_nodes):
        """
        Create equipment graph where edge weight = Jaccard similarity
        (shared ingredients / total unique ingredients between two equipment)
        """
        # Precompute ingredients for each equipment
        equipment_ingredients = {}
        for equip in equipment_nodes:
            equipment_ingredients[equip] = set(B.neighbors(equip))
        
        # Create graph with Jaccard similarity as weights
        G_jaccard = nx.Graph()
        G_jaccard.add_nodes_from(equipment_nodes)
        
        for eq1, eq2 in combinations(equipment_nodes, 2):
            ingredients1 = equipment_ingredients[eq1]
            ingredients2 = equipment_ingredients[eq2]
            
            if ingredients1 and ingredients2:  # both have ingredients
                intersection = len(ingredients1 & ingredients2)
                union = len(ingredients1 | ingredients2)
                jaccard_sim = intersection / union if union > 0 else 0
                
                if jaccard_sim > 0:  # only connect if they share ingredients
                    G_jaccard.add_edge(eq1, eq2, weight=jaccard_sim)
        
        return G_jaccard

    @classmethod
    def find_optimized_equipment_groups(
        cls,
        equipments,
        min_shared_resources=2,
        excluded_resource_ids=None,
        resolution=1.0,
        min_group_size=2,
        max_group_size=8,
        efficiency_threshold=0.3,
    ):
        """
        Find equipment groups optimized for resource sharing and bulk efficiency,
        while excluding specific resources from the sharing calculation.

        Args:
            equipments: List of equipment dictionaries
            min_shared_resources: Minimum number of non-excluded shared resources required
            excluded_resource_ids: Set of resource IDs to exclude from sharing calculation
            resolution: Community detection resolution parameter
            min_group_size: Minimum equipment per group
            max_group_size: Maximum equipment per group
            efficiency_threshold: Minimum resource sharing efficiency required
        """
        # Thin wrapper to preserve the original static-like API while
        # delegating to an instance for the implementation and helpers.
        processor = cls()
        return processor._find_optimized_equipment_groups(
            equipments,
            min_shared_resources=min_shared_resources,
            excluded_resource_ids=excluded_resource_ids,
            resolution=resolution,
            min_group_size=min_group_size,
            max_group_size=max_group_size,
            efficiency_threshold=efficiency_threshold,
        )

    def _find_optimized_equipment_groups(
        self,
        equipments,
        min_shared_resources=2,
        excluded_resource_ids=None,
        resolution=1.0,
        min_group_size=2,
        max_group_size=8,
        efficiency_threshold=0.3,
    ):
        """Instance implementation that is split into smaller helpers."""
        if excluded_resource_ids is None:
            excluded_resource_ids = set()

        # Create the bipartite graph from the equipment list
        B = self.create_bipartite_graph(equipments)

        # Identify equipment nodes in the bipartite graph
        equipment_nodes = {n for n, attr in B.nodes(data=True) if attr["bipartite"] == 0}

        # Build a similarity graph between equipments
        equipment_graph = self.create_jaccard_similarity_graph(B, equipment_nodes)

        # Use Louvain community detection
        partition = community.best_partition(equipment_graph, resolution=resolution, randomize=True)

        # Group equipment nodes by community id
        communities = self._partition_to_communities(partition)

        # Map equipment ids back to equipment details
        equipment_dict = {equip["ankama_id"]: equip for equip in equipments}
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
                group_equipments, excluded_resource_ids
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
            for resource in equipment["recipe"]:
                resource_id = resource["item_ankama_id"]
                quantity = resource["quantity"]

                # Update ingredient information
                ingredients[resource_id]["total_quantity"] += quantity
                ingredients[resource_id]["used_in_equipments"].append(equipment["name"])
                ingredients[resource_id]["quantity_per_equipment"][equipment["name"]] = quantity

                # Get resource name if not already set
                if ingredients[resource_id]["name"] is None:
                    ingredients[resource_id]["name"] = self.cache.get_resource_name(resource_id)

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
            for resource in equipment["recipe"]:
                resource_id = resource["item_ankama_id"]
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

    def print_optimized_groups(self, groups, excluded_resource_ids=None):
        """
        Print optimized groups with resource sharing information.
        """
        if excluded_resource_ids is None:
            excluded_resource_ids = set()

        print("OPTIMIZED EQUIPMENT GROUPS")
        print("=" * 50)
        print(f"Excluded resources from sharing calculation: {excluded_resource_ids}")
        print(f"Total groups found: {len(groups)}")
        print("\n")

        for i, group in enumerate(groups):
            print(f"Group {i+1}:")
            print(f"  - Equipment count: {len(group['equipments'])}")
            print(f"  - Shared resources (non-excluded): {group['shared_resources_count']}")
            print(f"  - Total shared resources: {group['total_shared_resources']}")
            print(f"  - Sharing efficiency: {group['sharing_efficiency']:.2%}")

            # List equipment in this group
            print("  - Equipment:")
            for equip in group["equipments"]:
                print(f"      {equip['name']} (Level: {equip['level']})")

            # List shared resources (excluding specified ones)
            shared_resources = self.get_shared_resources(group["equipments"], excluded_resource_ids)
            if shared_resources:
                print("  - Shared resources (non-excluded):")
                for resource_id, count in shared_resources.items():
                    resource_name = self.cache.get_resource_name(resource_id)
                    print(f"      {resource_name} (used by {count} equipment)")

            print()

    def get_shared_resources(self, group_equipments, excluded_resource_ids):
        """
        Get shared resources for a group, excluding specified resources.
        """
        resource_usage = defaultdict(int)

        for equipment in group_equipments:
            for resource in equipment["recipe"]:
                resource_id = resource["item_ankama_id"]
                resource_usage[resource_id] += 1

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

    def create_bipartite_graph(self, equipments):
        """Create a simple bipartite graph from equipment list.

        Equipment nodes will have attribute bipartite=0 and resource nodes
        bipartite=1. Edges will connect equipment -> resource.
        """
        B = nx.Graph()
        for equip in equipments:
            eq_id = equip.get("ankama_id")
            # Add equipment node
            B.add_node(eq_id, bipartite=0, type="equipment")

            for resource in equip.get("recipe", []):
                res_id = resource.get("item_ankama_id")
                # Add resource node and connect
                if not B.has_node(res_id):
                    B.add_node(res_id, bipartite=1, type="resource")
                B.add_edge(eq_id, res_id)

        return B

