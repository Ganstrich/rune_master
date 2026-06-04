"""Random group builder for exploratory equipment grouping.

Implements random selection of seed equipment followed by companion-finding
based on shared resources. Provides reproducible randomness via seed parameter.
"""

import random
import logging
from typing import List, Dict, Any, Optional, Set
from models import Equipment
from data.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class RandomGroupBuilder:
    """Builds equipment groups by random selection and resource matching.
    
    Process:
    1. Randomly select a seed equipment
    2. Find companion equipment sharing resources with seed
    3. Return group with metadata about selection method
    """

    def __init__(
        self,
        equipments: List[Equipment],
        excluded_resource_ids: Optional[Set[int]] = None,
        seed: Optional[int] = None,
        cache_manager: Optional[CacheManager] = None,
    ):
        """Initialize RandomGroupBuilder.
        
        Args:
            equipments: Pool of Equipment objects to draw from
            excluded_resource_ids: Resource IDs to exclude from sharing calculation
            seed: Random seed for reproducibility (None = unseeded)
            cache_manager: CacheManager for looking up resource names (optional)
        """
        self.equipments = equipments
        self.excluded_resource_ids = excluded_resource_ids or set()
        self.seed = seed
        self.cache_manager = cache_manager
        
        if seed is not None:
            random.seed(seed)
            logger.info(f"RandomGroupBuilder initialized with seed: {seed}")

    def select_random_seed(
        self,
        equipment_pool: List[Equipment],
        used_seeds: Optional[Set[int]] = None,
    ) -> Optional[Equipment]:
        """Select random seed equipment from pool.
        
        Args:
            equipment_pool: List of Equipment to select from
            used_seeds: Set of equipment IDs already used as seeds (avoids duplicates)
            
        Returns:
            Random Equipment object, or None if no available equipment
        """
        if not equipment_pool:
            logger.warning("Cannot select seed: empty equipment pool")
            return None

        used_seeds = used_seeds or set()
        available = [e for e in equipment_pool if e.ankama_id not in used_seeds]

        if not available:
            logger.warning(f"All {len(equipment_pool)} equipment used as seeds")
            return None

        seed_equipment = random.choice(available)
        logger.debug(f"Selected seed: {seed_equipment.name} (id={seed_equipment.ankama_id})")
        return seed_equipment

    def find_companions(
        self,
        seed_equipment: Equipment,
        equipment_pool: List[Equipment],
        min_shared_resources: int = 2,
        exclude_seed: bool = True,
    ) -> List[Equipment]:
        """Find companion equipment sharing resources with seed.
        
        Companion selection criteria:
        - Must share at least min_shared_resources with seed
        - Sorted by % resources shared (descending)
        - Optionally excludes seed itself
        
        Args:
            seed_equipment: The starting equipment
            equipment_pool: Pool to search for companions
            min_shared_resources: Minimum shared resources to qualify
            exclude_seed: Whether to exclude seed from companions
            
        Returns:
            List of companion Equipment, sorted by similarity (high to low)
        """
        # Get seed resources
        seed_resources = {req.resource_id for req in seed_equipment.recipe}
        seed_resources -= self.excluded_resource_ids

        if not seed_resources:
            logger.debug(f"Seed {seed_equipment.name} has no resources (after exclusions)")
            return []

        # Find companions
        companions = []

        for eq in equipment_pool:
            # Skip seed itself if requested
            if exclude_seed and eq.ankama_id == seed_equipment.ankama_id:
                continue

            # Get equipment resources
            eq_resources = {req.resource_id for req in eq.recipe}
            eq_resources -= self.excluded_resource_ids

            # Count shared resources
            shared_count = len(seed_resources & eq_resources)

            if shared_count >= min_shared_resources:
                # Calculate sharing efficiency (% of seed resources)
                efficiency = shared_count / len(seed_resources) if seed_resources else 0
                companions.append((eq, shared_count, efficiency))

        # Sort by shared count (descending), then by efficiency
        companions.sort(key=lambda x: (x[1], x[2]), reverse=True)

        result = [c[0] for c in companions]
        logger.debug(
            f"Found {len(result)} companions for {seed_equipment.name} "
            f"(sharing >= {min_shared_resources} resources)"
        )

        return result

    def build_random_group(
        self,
        equipment_pool: List[Equipment],
        seed_equipment: Optional[Equipment] = None,
        min_shared_resources: int = 2,
        max_group_size: int = 18,
    ) -> Optional[Dict[str, Any]]:
        """Build a single random group from seed and companions.
        
        Args:
            equipment_pool: Pool to draw from
            seed_equipment: If None, selects random seed from pool
            min_shared_resources: Minimum shared resources per companion
            max_group_size: Maximum group size (seed + companions)
            
        Returns:
            Dict with complete group data matching GroupMapper format, or None if unable to build group
        """
        # Select seed if not provided
        if seed_equipment is None:
            seed_equipment = self.select_random_seed(equipment_pool)
            if seed_equipment is None:
                return None

        # Find companions
        companions = self.find_companions(
            seed_equipment,
            equipment_pool,
            min_shared_resources=min_shared_resources,
            exclude_seed=True,
        )

        # Limit group size
        companions = companions[:max_group_size - 1]

        # Build group
        group_equipments = [seed_equipment] + companions

        # ENFORCE MINIMUM SIZE: A group must have at least 2 items
        if len(group_equipments) < 2:
            logger.debug(f"Rejecting group for {seed_equipment.name}: no companions found")
            return None

        # Calculate all metrics
        shared_resources = self._calculate_shared_resources(group_equipments)
        total_ingredients = self._aggregate_resources(group_equipments)
        sharing_efficiency = self._calculate_efficiency(group_equipments)
        average_density = self._calculate_average_density(group_equipments)

        return {
            "equipments": group_equipments,
            "shared_resources_count": len(shared_resources),
            "total_shared_resources": shared_resources,
            "sharing_efficiency": sharing_efficiency,
            "average_density": average_density,
            "total_ingredients": total_ingredients,
            "unique_ingredients_count": len(total_ingredients),
            "total_items_needed": sum(
                ing["total_quantity"] for ing in total_ingredients.values()
            ),
            # Random-specific metadata
            "selection_method": "random",
            "seed_equipment_id": seed_equipment.ankama_id,
            "randomness_seed": self.seed,
        }

    def build_multiple_random_groups(
        self,
        equipment_pool: List[Equipment],
        count: int = 10,
        min_shared_resources: int = 2,
        max_group_size: int = 18,
        avoid_seed_duplicates: bool = True,
    ) -> List[Dict[str, Any]]:
        """Build multiple random groups from same pool.
        
        Args:
            equipment_pool: Pool to draw from
            count: Number of random groups to generate
            min_shared_resources: Minimum shared resources per companion
            max_group_size: Maximum group size per group
            avoid_seed_duplicates: If True, don't reuse same seed equipment
            
        Returns:
            List of group dicts
        """
        groups = []
        used_seeds: Set[int] = set()

        for i in range(count):
            # Select seed (optionally avoiding duplicates)
            if avoid_seed_duplicates:
                seed = self.select_random_seed(equipment_pool, used_seeds=used_seeds)
            else:
                seed = self.select_random_seed(equipment_pool)

            if seed is None:
                logger.warning(
                    f"Could not generate group {i + 1}/{count}: "
                    f"no available seeds (used {len(used_seeds)} so far)"
                )
                break

            # Build group
            group = self.build_random_group(
                equipment_pool,
                seed_equipment=seed,
                min_shared_resources=min_shared_resources,
                max_group_size=max_group_size,
            )

            if group:
                groups.append(group)
                if avoid_seed_duplicates:
                    used_seeds.add(seed.ankama_id)
                logger.info(f"Generated group {len(groups)}: {seed.name} + {len(group['equipments']) - 1} companions")

        logger.info(f"Generated {len(groups)}/{count} random groups")
        return groups

    @staticmethod
    def _calculate_shared_resources(equipments: List[Equipment]) -> set:
        """Calculate resources shared by all equipments in group."""
        if not equipments:
            return set()

        # Start with first equipment's resources
        shared = {req.resource_id for req in equipments[0].recipe}

        # Intersect with all others
        for eq in equipments[1:]:
            eq_resources = {req.resource_id for req in eq.recipe}
            shared = shared & eq_resources

        return shared

    def _aggregate_resources(self, equipments: List[Equipment]) -> Dict[int, dict]:
        """Aggregate all resources needed for group.
        
        Returns dict mapping resource_id -> {name, total_quantity, quantity_per_equipment}.
        Matches format from GroupMapper for compatibility with visualization.
        Uses cache manager to look up real resource names.
        """
        aggregated = {}

        for eq in equipments:
            for req in eq.recipe:
                resource_id = req.resource_id
                
                if resource_id not in aggregated:
                    # Try to get resource name from cache
                    resource_name = f'Resource {resource_id}'
                    if self.cache_manager:
                        try:
                            cached_name = self.cache_manager.get_resource_name(resource_id)
                            if cached_name:
                                resource_name = cached_name
                        except Exception as e:
                            logger.debug(f"Could not fetch resource name for {resource_id}: {e}")
                    
                    aggregated[resource_id] = {
                        'name': resource_name,
                        'total_quantity': 0,
                        'quantity_per_equipment': {}
                    }
                
                # Add to total
                aggregated[resource_id]['total_quantity'] += req.quantity
                
                # Track quantity per equipment
                eq_name = eq.name if hasattr(eq, 'name') else f'Equipment {eq.ankama_id}'
                if eq_name not in aggregated[resource_id]['quantity_per_equipment']:
                    aggregated[resource_id]['quantity_per_equipment'][eq_name] = 0
                aggregated[resource_id]['quantity_per_equipment'][eq_name] += req.quantity

        return aggregated

    @staticmethod
    def _calculate_efficiency(equipments: List[Equipment]) -> float:
        """Calculate sharing efficiency of group.

        Efficiency = resources used by 2+ equipment / total unique resources

        Represents fraction of total unique resources that are shared across any subset of equipment.
        This is the canonical definition used across all experts for consistency.

        Higher = better (more items share same resources)
        """
        if not equipments:
            return 0.0

        # Count how many equipment use each resource
        resource_usage = {}
        for eq in equipments:
            for req in eq.recipe:
                resource_usage[req.resource_id] = resource_usage.get(req.resource_id, 0) + 1

        # Count resources used by 2+ equipment
        shared_count = sum(1 for count in resource_usage.values() if count >= 2)

        # Calculate total unique resources
        total_unique = len(resource_usage)

        if total_unique == 0:
            return 0.0

        efficiency = shared_count / total_unique
        return efficiency

    @staticmethod
    def _calculate_average_density(equipments: List[Equipment]) -> float:
        """Calculate average stat weight density of group.
        
        Density = average(stat_weight / level) across all equipments.
        """
        if not equipments:
            return 0.0

        densities = []
        for eq in equipments:
            if eq.stat_weight is not None and eq.level > 0:
                density = eq.stat_weight / eq.level
                densities.append(density)

        if not densities:
            return 0.0

        return sum(densities) / len(densities)
