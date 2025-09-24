from collections import defaultdict
import networkx as nx
from networkx.algorithms import bipartite
from collections import defaultdict
import community
from utils import CacheManager
from cdlib import algorithms
from tqdm.auto import tqdm


class DataProcessor:
    @staticmethod
    def find_optimized_equipment_groups(
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
        if excluded_resource_ids is None:
            excluded_resource_ids = set()

        # Create the bipartite graph
        B = DataProcessor().create_bipartite_graph(equipments)

        # Get all equipment nodes
        equipment_nodes = {
            n for n, attr in B.nodes(data=True) if attr["bipartite"] == 0
        }

        # Project the bipartite graph to equipment graph with weights
        equipment_graph = bipartite.weighted_projected_graph(B, equipment_nodes)

        # Use Louvain community detection
        partition = community.best_partition(equipment_graph, resolution=resolution, randomize=True)

        # Group equipment nodes by community
        communities = {}
        for node, community_id in partition.items():
            communities.setdefault(community_id, []).append(node)

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

            # Skip if group doesn't meet size requirements
            if not (min_group_size <= len(group_equipments) <= max_group_size):
                continue

            # Calculate shared resources (excluding specified resources)
            shared_count, total_shared, efficiency = (
                DataProcessor.calculate_shared_resources(
                    group_equipments, excluded_resource_ids
                )
            )

            # Calculate total ingredients needed for the group
            total_ingredients = DataProcessor.calculate_total_ingredients(
                group_equipments
            )

            # Apply multiple filters
            if (
                shared_count >= min_shared_resources
                and efficiency >= efficiency_threshold
            ):
                groups.append(
                    {
                        "equipments": group_equipments,
                        "shared_resources_count": shared_count,
                        "total_shared_resources": total_shared,
                        "sharing_efficiency": efficiency,
                        "total_ingredients": total_ingredients,
                        "unique_ingredients_count": len(total_ingredients),
                        "total_items_needed": sum(
                            ingredient["total_quantity"]
                            for ingredient in total_ingredients.values()
                        ),
                    }
                )

        # Sort groups by sharing efficiency (descending)
        groups.sort(key=lambda x: x["sharing_efficiency"], reverse=True)

        return groups

    @staticmethod
    def calculate_total_ingredients(group_equipments):
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
                ingredients[resource_id]["quantity_per_equipment"][
                    equipment["name"]
                ] = quantity

                # Get resource name if not already set
                if ingredients[resource_id]["name"] is None:
                    ingredients[resource_id]["name"] = CacheManager.get_resource_name(
                        resource_id
                    )

        return dict(ingredients)

    @staticmethod
    def calculate_shared_resources(group_equipments, excluded_resource_ids):
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
        shared_resources = {
            rid: count
            for rid, count in resource_usage.items()
            if count > 1 and rid not in excluded_resource_ids
        }

        # Calculate total shared resources (including excluded ones)
        total_shared_resources = {
            rid: count for rid, count in resource_usage.items() if count > 1
        }

        # Calculate sharing efficiency
        total_unique = len(all_resources)
        shared_count = len(shared_resources)
        efficiency = shared_count / total_unique if total_unique > 0 else 0

        return shared_count, len(total_shared_resources), efficiency

    @staticmethod
    def print_optimized_groups(groups, excluded_resource_ids=None):
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
            print(
                f"  - Shared resources (non-excluded): {group['shared_resources_count']}"
            )
            print(f"  - Total shared resources: {group['total_shared_resources']}")
            print(f"  - Sharing efficiency: {group['sharing_efficiency']:.2%}")

            # List equipment in this group
            print("  - Equipment:")
            for equip in group["equipments"]:
                print(f"      {equip['name']} (Level: {equip['level']})")

            # List shared resources (excluding specified ones)
            shared_resources = DataProcessor().get_shared_resources(
                group["equipments"], excluded_resource_ids
            )
            if shared_resources:
                print("  - Shared resources (non-excluded):")
                for resource_id, count in shared_resources.items():
                    resource_name = CacheManager.get_resource_name(resource_id)
                    print(f"      {resource_name} (used by {count} equipment)")

            print()

    @staticmethod
    def get_shared_resources(group_equipments, excluded_resource_ids):
        """
        Get shared resources for a group, excluding specified resources.
        """
        resource_usage = defaultdict(int)

        for equipment in group_equipments:
            for resource in equipment["recipe"]:
                resource_id = resource["item_ankama_id"]
                resource_usage[resource_id] += 1

        # Return only shared resources that aren't excluded
        return {
            rid: count
            for rid, count in resource_usage.items()
            if count > 1 and rid not in excluded_resource_ids
        }

