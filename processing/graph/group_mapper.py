"""Group mapping module for converting communities to equipment groups.

This module handles the conversion of detected communities into optimized
equipment groups with ingredient analysis and efficiency metrics.
"""

from typing import Any, Dict, List, Tuple
from models import Equipment
from processing.blocks.recipes import iter_recipe
from processing.metrics.group_metrics import GroupMetrics
from processing.policy import GroupAcceptancePolicy
from processing.metrics.quality_metrics import GroupQualityWeights


class GroupMapper:
    """Map communities to optimized equipment groups."""

    def __init__(
        self,
        equipments: List[Equipment],
        excluded_resource_ids: set = None,
        quality_weights: GroupQualityWeights | None = None,
        acceptance_policy: GroupAcceptancePolicy | None = None,
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
        self.acceptance_policy = acceptance_policy

    def calculate_shared_resources(
        self,
        group_equipments: List[Equipment]
    ) -> Tuple[int, set[int], float]:
        """Calculate shared resources for a group.

        **CANONICAL DEFINITION** of sharing efficiency used across all experts.
        All other experts must match this definition for consistent MoE gating
        network fitness scores.

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

        Communities larger than max_group_size are split into subgroups
        rather than rejected outright.
        """
        policy = self.acceptance_policy or GroupAcceptancePolicy.from_values(
            min_group_size, max_group_size, min_shared_resources,
            efficiency_threshold, quality_threshold,
        )
        return self._process_communities(
            communities, policy, min_group_size, cache_manager, api_client
        )

    def map_communities_inclusive(
        self,
        communities: Dict[int, List[int]],
        min_group_size: int = 1,
        max_group_size: int = 15,
        min_shared_resources: int = 1,
        efficiency_threshold: float = 0.15,
        quality_threshold: float = 0.0,
        cache_manager=None,
        api_client=None
    ) -> List[Dict[str, Any]]:
        """Convert communities to groups with inclusive filtering.

        Maximizes retention of equipment by using permissive thresholds and
        splitting large groups.

        This path is currently unreachable: ``config.use_inclusive_mapping``
        defaults to False and nothing sets it True. The threshold previously
        defaulted to 0.10 here while ``map_communities`` used 0.15, which made
        the two entry points disagree on policy; they now share one value
        (metrics-revision §3.6).

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
        policy = self.acceptance_policy or GroupAcceptancePolicy.from_values(
            min_group_size, max_group_size, min_shared_resources,
            efficiency_threshold, quality_threshold,
        )
        return self._process_communities(
            communities, policy, min_group_size, cache_manager, api_client
        )

    def _process_communities(
        self,
        communities: Dict[int, List[int]],
        policy,
        min_group_size: int,
        cache_manager,
        api_client,
    ) -> List[Dict[str, Any]]:
        """Shared community processing for both mapping paths."""
        groups = []

        for _community_id, equip_ids in communities.items():
            group_equipments = self._resolve_equipment_objects(equip_ids)

            if len(group_equipments) > policy.max_size:
                subgroups = self._split_large_community(
                    group_equipments, max_size=policy.max_size
                )
                for subgroup in subgroups:
                    if len(subgroup) < min_group_size:
                        continue
                    group = self.create_group(
                        subgroup, cache_manager=cache_manager, api_client=api_client,
                    )
                    if policy.accepts(group):
                        groups.append(group)
                continue

            group = self.create_group(
                group_equipments, cache_manager=cache_manager, api_client=api_client,
            )
            if policy.accepts(group):
                groups.append(group)

        groups.sort(key=lambda group: group["quality_score"], reverse=True)
        return groups

    def _split_large_community(
        self,
        large_group: List[Equipment],
        max_size: int = 8
    ) -> List[List[Equipment]]:
        """Split a large community into resource-cohesive subgroups.

        The previous implementation sliced the community into contiguous blocks
        of ``max_size``. Because Louvain returns communities in arbitrary order,
        consecutive items frequently shared no resources at all, and every chunk
        then failed the acceptance policy — probe R1 measured a 100% loss on an
        869-item community split at max_size=8.

        This version greedily packs items that share resources, seeding each
        subgroup from the member with the highest remaining resource degree so
        each chunk starts from the best-connected item.

        Args:
            large_group: Large group of Equipment objects
            max_size: Maximum size for each subgroup

        Returns:
            List of subgroups, each at most ``max_size`` items
        """
        if len(large_group) <= max_size:
            return [large_group]

        remaining = {id(equipment): equipment for equipment in large_group}
        resource_sets = {
            key: set(int(request.resource_id) for request in (equipment.recipe or []))
            for key, equipment in remaining.items()
        }
        # Seed order: most resources first, so each chunk starts cohesive.
        ordered_keys = sorted(remaining, key=lambda key: -len(resource_sets[key]))

        subgroups: List[List[Equipment]] = []
        for seed_key in ordered_keys:
            if seed_key not in remaining:
                continue

            seed = remaining.pop(seed_key)
            members = [seed]
            pooled = set(resource_sets[seed_key])

            while len(members) < max_size:
                # Prefer candidates sharing the most resources with the chunk.
                best_key, best_overlap = None, 0
                for key, equipment in remaining.items():
                    overlap = len(resource_sets[key] & pooled)
                    if overlap > best_overlap:
                        best_key, best_overlap = key, overlap
                if best_key is None:
                    break
                pooled |= resource_sets.pop(best_key)
                members.append(remaining.pop(best_key))

            subgroups.append(members)

        return subgroups

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
