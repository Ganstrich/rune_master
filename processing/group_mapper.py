"""Group mapping module for converting communities to equipment groups.

This module handles the conversion of detected communities into optimized
equipment groups with ingredient analysis and efficiency metrics.
"""

from typing import Any, Dict, List, Tuple
from tqdm.auto import tqdm
from models import Equipment
from processing.blocks.recipes import iter_recipe
from processing.group_metrics import GroupMetrics
from processing.quality_metrics import GroupQualityWeights


class GroupMapper:
    """Map communities to optimized equipment groups."""

    def __init__(
        self,
        equipments: List[Equipment],
        excluded_resource_ids: set = None,
        quality_weights: GroupQualityWeights | None = None,
    ):
        """Initialize group mapper.

        Args:
            equipments: List of all Equipment objects
            excluded_resource_ids: Set of resource IDs to exclude from sharing calculations
        """
        self.equipments = equipments
        self.equipment_dict = {int(e.ankama_id): e for e in equipments}
        self.excluded_resource_ids = excluded_resource_ids or set()
        self.quality_weights = quality_weights

    def calculate_shared_resources(
        self,
        group_equipments: List[Equipment]
    ) -> Tuple[int, set[int], float]:
        """Calculate shared resources for a group.

        **CANONICAL DEFINITION** of sharing efficiency used across all experts.
        All other experts (RandomGroupBuilder, GeneticExpert, etc.) must match
        this definition for consistent MoE gating network fitness scores.

        Definition:
            sharing_efficiency = resources_used_by_2plus / total_unique_resources

        Where:
            - resources_used_by_2plus: count of resource IDs that appear in the
              recipes of 2 or more equipment in the group (excluding excluded_resource_ids)
            - total_unique_resources: count of distinct resource IDs across all
              equipment in the group

        Returns:
            - shared_count: Resources used by 2+ equipment (excluding excluded_ids)
            - total_shared_resources: Resource IDs used by 2+ equipment (including excluded_ids)
            - efficiency: shared_count / total_unique_resources in group
        """
        shared_resources = GroupMetrics.shared_resources(
            group_equipments, self.excluded_resource_ids
        )
        all_shared_resources = GroupMetrics.shared_resources(group_equipments)
        efficiency = GroupMetrics.sharing_efficiency(
            group_equipments, self.excluded_resource_ids
        )
        return len(shared_resources), all_shared_resources, efficiency

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
        return GroupMetrics.average_density(group_equipments)

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
        return GroupMetrics.aggregate_resources(group_equipments, cache_manager)

    def create_group(
        self,
        group_equipments: List[Equipment],
        cache_manager=None,
        api_client=None
    ) -> Dict[str, Any]:
        """Create a formatted group dictionary from a list of Equipment objects.
        
        Args:
            group_equipments: List of Equipment dataclasses
            cache_manager: Optional CacheManager for resource names
            api_client: Optional API client
            
        Returns:
            Dictionary with all group metadata (efficiency, ingredients, etc.)
        """
        return GroupMetrics.build_group_dict(
            group_equipments,
            cache_manager=cache_manager,
            api_client=api_client,
            excluded_resource_ids=self.excluded_resource_ids,
            quality_weights=self.quality_weights,
        )

    def map_communities(
        self,
        communities: Dict[int, List[int]],
        min_group_size: int = 2,
        max_group_size: int = 18,
        min_shared_resources: int = 2,
        efficiency_threshold: float = 0.15,
        quality_threshold: float = 0.0,
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
            shared_count, shared_resources, efficiency = self.calculate_shared_resources(
                group_equipments
            )

            # Apply quality filters
            if shared_count < min_shared_resources:
                continue

            if efficiency < efficiency_threshold:
                continue

            group = self.create_group(
                group_equipments,
                cache_manager=cache_manager,
                api_client=api_client
            )
            if group["quality_score"] < quality_threshold:
                continue
            groups.append(group)

        groups.sort(key=lambda group: group["quality_score"], reverse=True)

        print(f"✓ Mapped {len(groups)} groups from {len(communities)} communities")

        return groups

    def map_communities_inclusive(
        self,
        communities: Dict[int, List[int]],
        min_group_size: int = 1,
        max_group_size: int = 15,
        min_shared_resources: int = 1,
        efficiency_threshold: float = 0.1,
        quality_threshold: float = 0.0,
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
                        min_shared_resources, efficiency_threshold, quality_threshold,
                        cache_manager, api_client
                    )
                continue

            # Process normal-sized group
            self._process_subgroup(
                group_equipments, groups, stats,
                min_shared_resources, efficiency_threshold, quality_threshold,
                cache_manager, api_client
            )

        groups.sort(key=lambda group: group["quality_score"], reverse=True)

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
        quality_threshold: float,
        cache_manager,
        api_client=None
    ) -> None:
        """Process a subgroup and add to groups list if it meets criteria."""
        shared_count, shared_resources, efficiency = self.calculate_shared_resources(
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

        group = self.create_group(
            group_equipments,
            cache_manager=cache_manager,
            api_client=api_client
        )
        if group["quality_score"] < quality_threshold:
            return
        groups.append(group)

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
