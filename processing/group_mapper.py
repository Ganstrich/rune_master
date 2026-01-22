"""Group mapping module for converting communities to equipment groups.

This module handles the conversion of detected communities into optimized
equipment groups with ingredient analysis and efficiency metrics.
"""

from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional
from tqdm.auto import tqdm
from models import Equipment, ResourceRequirement


class GroupMapper:
    """Map communities to optimized equipment groups."""

    def __init__(
        self,
        equipments: List[Equipment],
        excluded_resource_ids: set = None
    ):
        """Initialize group mapper.

        Args:
            equipments: List of all Equipment objects
            excluded_resource_ids: Set of resource IDs to exclude from sharing calculations
        """
        self.equipments = equipments
        self.equipment_dict = {int(e.ankama_id): e for e in equipments}
        self.excluded_resource_ids = excluded_resource_ids or set()

    def calculate_shared_resources(
        self,
        group_equipments: List[Equipment]
    ) -> Tuple[int, int, float]:
        """Calculate shared resources for a group.

        Returns:
            - shared_count: Resources used by 2+ equipment (excluding excluded_ids)
            - total_shared_count: Resources used by 2+ equipment (including excluded_ids)
            - efficiency: shared_count / total_unique_resources in group
        """
        resource_usage = defaultdict(int)
        all_resources = set()

        for equipment in group_equipments:
            for resource_id, _qty in self._iter_equipment_recipe(equipment):
                resource_id = int(resource_id)
                resource_usage[resource_id] += 1
                all_resources.add(resource_id)

        # Count shared resources (used by 2+ equipment)
        shared_resources = {
            rid: count for rid, count in resource_usage.items()
            if count > 1 and rid not in self.excluded_resource_ids
        }

        total_shared_resources = {
            rid: count for rid, count in resource_usage.items()
            if count > 1
        }

        # Calculate efficiency
        total_unique = len(all_resources)
        shared_count = len(shared_resources)
        efficiency = (shared_count / total_unique) if total_unique > 0 else 0

        return shared_count, len(total_shared_resources), efficiency

    def calculate_average_density(
        self,
        group_equipments: List[Equipment]
    ) -> float:
        """Calculate average density of equipment in the group.

        Density = sum of stat weights for all effects in an equipment
        Average Density = mean stat_weight across all equipment in group

        Args:
            group_equipments: List of Equipment objects

        Returns:
            Average stat_weight across all equipment in the group
        """
        if not group_equipments:
            return 0.0

        total_weight = sum((eq.stat_weight or 0) for eq in group_equipments)
        return total_weight / len(group_equipments)

    def calculate_total_ingredients(
        self,
        group_equipments: List[Equipment],
        cache_manager=None,
        api_client=None
    ) -> Dict[int, Dict[str, Any]]:
        """Calculate total ingredients needed for all equipment in group.

        Args:
            group_equipments: List of Equipment objects
            cache_manager: Optional CacheManager for resource name lookup (RECOMMENDED)
            api_client: Optional API client (not used - resources should be cached)

        Returns:
            Dict mapping resource_id -> {name, total_quantity, quantity_per_equipment}
        """
        ingredients = defaultdict(
            lambda: {
                "name": None,
                "total_quantity": 0,
                "used_in_equipments": [],
                "quantity_per_equipment": {},
            }
        )

        # Process equipment recipes
        for equipment in group_equipments:
            for resource_id, quantity in self._iter_equipment_recipe(equipment):
                resource_id = int(resource_id)
                ingredients[resource_id]["total_quantity"] += int(quantity)

                eq_name = getattr(equipment, "name", None) or str(
                    getattr(equipment, "ankama_id", "?")
                )
                ingredients[resource_id]["used_in_equipments"].append(eq_name)
                ingredients[resource_id]["quantity_per_equipment"][eq_name] = int(quantity)

                # Get resource name from cache
                if ingredients[resource_id]["name"] is None:
                    if cache_manager:
                        try:
                            resource_data = cache_manager.get_resource(resource_id)
                            if resource_data:
                                ingredients[resource_id]["name"] = resource_data.get('name', f'Resource {resource_id}')
                        except Exception:
                            pass

                    # Fallback to generic name if cache lookup failed or no cache manager
                    if ingredients[resource_id]["name"] is None:
                        ingredients[resource_id]["name"] = f"Resource {resource_id}"

        return dict(ingredients)

    def map_communities(
        self,
        communities: Dict[int, List[int]],
        min_group_size: int = 2,
        max_group_size: int = 18,
        min_shared_resources: int = 2,
        efficiency_threshold: float = 0.15,
        cache_manager=None,
        api_client=None
    ) -> List[Dict[str, Any]]:
        """Convert communities to equipment groups with filtering.

        Args:
            communities: Dict from CommunityDetector.partition_to_communities()
            min_group_size: Minimum equipment per group
            max_group_size: Maximum equipment per group
            min_shared_resources: Minimum shared resources required
            efficiency_threshold: Minimum efficiency ratio required
            cache_manager: Optional CacheManager for resource names
            api_client: Optional API client to fetch resource names

        Returns:
            List of group dicts with equipment, ingredients, efficiency metrics
        """
        groups = []

        for community_id, equip_ids in tqdm(
            communities.items(),
            desc="Processing communities",
            total=len(communities),
            unit="community",
            leave=True,
        ):
            group_equipments = self._resolve_equipment_objects(equip_ids)

            # Apply size filters
            if not (min_group_size <= len(group_equipments) <= max_group_size):
                continue

            # Calculate metrics
            shared_count, total_shared, efficiency = self.calculate_shared_resources(
                group_equipments
            )

            # Apply quality filters
            if shared_count < min_shared_resources:
                continue

            if efficiency < efficiency_threshold:
                continue

            # Calculate ingredients and density
            total_ingredients = self.calculate_total_ingredients(
                group_equipments,
                cache_manager=cache_manager,
                api_client=api_client
            )
            average_density = self.calculate_average_density(group_equipments)

            groups.append({
                "equipments": group_equipments,
                "shared_resources_count": shared_count,
                "total_shared_resources": total_shared,
                "sharing_efficiency": efficiency,
                "average_density": average_density,
                "total_ingredients": total_ingredients,
                "unique_ingredients_count": len(total_ingredients),
                "total_items_needed": sum(
                    ing["total_quantity"] for ing in total_ingredients.values()
                ),
            })

        # Sort by efficiency descending
        groups.sort(key=lambda x: x["sharing_efficiency"], reverse=True)

        print(f"✓ Mapped {len(groups)} groups from {len(communities)} communities")

        return groups

    def map_communities_inclusive(
        self,
        communities: Dict[int, List[int]],
        min_group_size: int = 1,
        max_group_size: int = 15,
        min_shared_resources: int = 1,
        efficiency_threshold: float = 0.1,
        cache_manager=None,
        api_client=None
    ) -> List[Dict[str, Any]]:
        """Convert communities to groups with inclusive filtering.

        Maximizes retention of equipment by using permissive thresholds and
        splitting large groups.

        Args:
            communities: Dict from CommunityDetector.partition_to_communities()
            min_group_size: Minimum equipment (1 allows singletons)
            max_group_size: Maximum equipment (large groups are split)
            min_shared_resources: Minimum shared resources
            efficiency_threshold: Low threshold to keep more groups
            cache_manager: Optional CacheManager

        Returns:
            List of group dicts (more numerous with inclusive filtering)
        """
        groups = []
        stats = {
            "total_equipments": len(self.equipments),
            "processed": 0,
            "excluded_by_size": 0,
            "excluded_by_resources": 0,
            "excluded_by_efficiency": 0,
        }

        for community_id, equip_ids in tqdm(
            communities.items(),
            desc="Processing communities (inclusive)",
            total=len(communities),
            unit="community",
            leave=True,
        ):
            group_equipments = self._resolve_equipment_objects(equip_ids)
            group_size = len(group_equipments)

            # Check minimum size
            if group_size < min_group_size:
                stats["excluded_by_size"] += group_size
                continue

            # Split large groups
            if group_size > max_group_size:
                subgroups = self._split_large_community(
                    group_equipments,
                    max_size=max_group_size
                )
                for subgroup in subgroups:
                    self._process_subgroup(
                        subgroup, groups, stats,
                        min_shared_resources, efficiency_threshold,
                        cache_manager, api_client
                    )
                continue

            # Process normal-sized group
            self._process_subgroup(
                group_equipments, groups, stats,
                min_shared_resources, efficiency_threshold,
                cache_manager, api_client
            )

        # Sort by efficiency descending
        groups.sort(key=lambda x: x["sharing_efficiency"], reverse=True)

        # Print statistics
        self._print_retention_stats(stats)

        return groups

    def _process_subgroup(
        self,
        group_equipments: List[Equipment],
        groups: List[Dict],
        stats: Dict,
        min_shared: int,
        efficiency_threshold: float,
        cache_manager,
        api_client=None
    ) -> None:
        """Process a subgroup and add to groups list if it meets criteria."""
        shared_count, total_shared, efficiency = self.calculate_shared_resources(
            group_equipments
        )

        # Check minimum shared resources
        if shared_count < min_shared:
            stats["excluded_by_resources"] += len(group_equipments)
            return

        # Check minimum efficiency
        if efficiency < efficiency_threshold:
            stats["excluded_by_efficiency"] += len(group_equipments)
            return

        # Calculate ingredients and density
        total_ingredients = self.calculate_total_ingredients(
            group_equipments,
            cache_manager=cache_manager,
            api_client=api_client
        )
        average_density = self.calculate_average_density(group_equipments)

        groups.append({
            "equipments": group_equipments,
            "shared_resources_count": shared_count,
            "total_shared_resources": total_shared,
            "sharing_efficiency": efficiency,
            "average_density": average_density,
            "total_ingredients": total_ingredients,
            "unique_ingredients_count": len(total_ingredients),
            "total_items_needed": sum(
                ing["total_quantity"] for ing in total_ingredients.values()
            ),
            "group_size": len(group_equipments),
        })

        stats["processed"] += len(group_equipments)

    def _split_large_community(
        self,
        large_group: List[Equipment],
        max_size: int = 8
    ) -> List[List[Equipment]]:
        """Split a large community into smaller subgroups.

        Args:
            large_group: Large group of Equipment objects
            max_size: Maximum size for each subgroup

        Returns:
            List of subgroups
        """
        if len(large_group) <= max_size:
            return [large_group]

        subgroups = []
        for i in range(0, len(large_group), max_size):
            subgroup = large_group[i : i + max_size]
            if len(subgroup) >= 1:
                subgroups.append(subgroup)

        return subgroups

    def _print_retention_stats(self, stats: Dict) -> None:
        """Print equipment retention statistics."""
        total = stats["total_equipments"]
        processed = stats["processed"]
        retention_rate = (processed / total) if total > 0 else 0

        print(f"\n=== GROUP MAPPING STATISTICS ===")
        print(f"Equipment processed: {processed}/{total} ({retention_rate:.1%})")
        print(f"Equipment excluded by size: {stats['excluded_by_size']} ({stats['excluded_by_size']/total:.1%})")
        print(f"Equipment excluded by resources: {stats['excluded_by_resources']} ({stats['excluded_by_resources']/total:.1%})")
        print(f"Equipment excluded by efficiency: {stats['excluded_by_efficiency']} ({stats['excluded_by_efficiency']/total:.1%})")

    def _resolve_equipment_objects(
        self,
        equip_ids: List[int]
    ) -> List[Equipment]:
        """Resolve equipment IDs to Equipment objects.

        Handles both int and str IDs.

        Args:
            equip_ids: List of equipment IDs

        Returns:
            List of Equipment objects
        """
        group_equipments = []
        for equip_id in equip_ids:
            if isinstance(equip_id, str):
                try:
                    equip_id_int = int(equip_id)
                    if equip_id_int in self.equipment_dict:
                        group_equipments.append(self.equipment_dict[equip_id_int])
                except ValueError:
                    continue
            elif equip_id in self.equipment_dict:
                group_equipments.append(self.equipment_dict[equip_id])

        return group_equipments

    @staticmethod
    def _iter_equipment_recipe(equipment: Equipment):
        """Iterate over (resource_id, quantity) pairs in equipment recipe.

        Handles both dataclass and dict formats.

        Args:
            equipment: Equipment dataclass object

        Yields:
            Tuples of (resource_id, quantity)
        """
        if isinstance(equipment, Equipment):
            for req in (equipment.recipe or []):
                if isinstance(req, ResourceRequirement):
                    yield req.resource_id, req.quantity
                elif isinstance(req, dict):
                    try:
                        yield int(req.get("item_ankama_id")), int(req.get("quantity", 1))
                    except (ValueError, TypeError):
                        continue
                else:
                    # Try attribute access
                    rid = getattr(req, "resource_id", None) or getattr(
                        req, "item_ankama_id", None
                    )
                    qty = getattr(req, "quantity", 1)
                    if rid is not None:
                        yield int(rid), int(qty)
            return

        # Handle dict format
        for item in (equipment.get("recipe") or []):
            try:
                yield int(item.get("item_ankama_id")), int(item.get("quantity", 1))
            except (ValueError, TypeError):
                continue
