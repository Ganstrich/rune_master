"""Random group builder for exploratory equipment grouping.

Implements random selection of seed equipment followed by companion-finding
based on shared resources. Provides reproducible randomness via seed parameter.
"""

import random
import logging
from typing import List, Dict, Any, Optional, Set
from models import Equipment
from data.cache_manager import CacheManager
from processing.group_metrics import GroupMetrics
from processing.quality_metrics import GroupQualityWeights

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
        quality_weights: GroupQualityWeights | None = None,
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
        self.quality_weights = quality_weights
        
        if seed is not None:
            random.seed(seed)
            logger.info(f"RandomGroupBuilder initialized with seed: {seed}")

    def _build_resource_index(
        self, equipment_pool: List[Equipment]
    ) -> Dict[int, List[int]]:
        """Build inverted index: resource_id -> list of equipment IDs in pool."""
        index: Dict[int, List[int]] = {}
        pool_ids = {e.ankama_id for e in equipment_pool}
        for eq in equipment_pool:
            for req in eq.recipe:
                rid = req.resource_id
                if rid not in index:
                    index[rid] = []
                index[rid].append(eq.ankama_id)
        return index

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
        resource_index: Optional[Dict[int, List[int]]] = None,
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
            resource_index: Optional inverted index (resource_id -> [equipment_ids])
            
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
        pool_ids = {e.ankama_id for e in equipment_pool}
        equipment_map = {e.ankama_id: e for e in equipment_pool}

        if resource_index:
            # Use inverted index to find candidates
            candidate_ids = set()
            for rid in seed_resources:
                if rid in resource_index:
                    candidate_ids.update(resource_index[rid])
            # Filter to pool
            candidate_ids &= pool_ids
            if exclude_seed:
                candidate_ids.discard(seed_equipment.ankama_id)
            
            candidates = [equipment_map[eid] for eid in candidate_ids]
        else:
            # Fallback to full scan
            candidates = equipment_pool

        for eq in candidates:
            # Skip seed itself if requested
            if exclude_seed and eq.ankama_id == seed_equipment.ankama_id:
                continue

            # Get equipment resources
            eq_resources = {req.resource_id for req in eq.recipe}
            eq_resources -= self.excluded_resource_ids

            shared_count = len(seed_resources & eq_resources)
            if shared_count >= min_shared_resources:
                efficiency = shared_count / len(seed_resources) if seed_resources else 0
                companions.append((eq, shared_count, efficiency))

        companions.sort(key=lambda item: (item[1], item[2]), reverse=True)
        return [companion[0] for companion in companions]

    def build_random_group(
        self,
        equipment_pool: List[Equipment],
        seed_equipment: Optional[Equipment] = None,
        min_shared_resources: int = 2,
        max_group_size: int = 18,
        resource_index: Optional[Dict[int, List[int]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Build a single random group from a seed and its companions."""
        if seed_equipment is None:
            seed_equipment = self.select_random_seed(equipment_pool)
            if seed_equipment is None:
                return None

        companions = self.find_companions(
            seed_equipment,
            equipment_pool,
            min_shared_resources=min_shared_resources,
            exclude_seed=True,
            resource_index=resource_index,
        )[:max_group_size - 1]
        group_equipments = [seed_equipment] + companions

        if len(group_equipments) < 2:
            logger.debug(f"Rejecting group for {seed_equipment.name}: no companions found")
            return None

        group = GroupMetrics.build_group_dict(
            group_equipments,
            cache_manager=self.cache_manager,
            excluded_resource_ids=self.excluded_resource_ids,
            quality_weights=self.quality_weights,
        )
        group.update({
            "selection_method": "random",
            "seed_equipment_id": seed_equipment.ankama_id,
            "randomness_seed": self.seed,
        })
        return group

    def build_multiple_random_groups(
        self,
        equipment_pool: List[Equipment],
        count: int = 10,
        min_shared_resources: int = 2,
        max_group_size: int = 18,
        avoid_seed_duplicates: bool = True,
    ) -> List[Dict[str, Any]]:
        """Build multiple random groups from the same equipment pool."""
        groups = []
        used_seeds: Set[int] = set()
        resource_index = self._build_resource_index(equipment_pool)

        for index in range(count):
            seed = self.select_random_seed(
                equipment_pool,
                used_seeds=used_seeds if avoid_seed_duplicates else None,
            )
            if seed is None:
                logger.warning(
                    f"Could not generate group {index + 1}/{count}: "
                    f"no available seeds (used {len(used_seeds)} so far)"
                )
                break

            group = self.build_random_group(
                equipment_pool,
                seed_equipment=seed,
                min_shared_resources=min_shared_resources,
                max_group_size=max_group_size,
                resource_index=resource_index,
            )
            if group:
                groups.append(group)
                if avoid_seed_duplicates:
                    used_seeds.add(seed.ankama_id)
                logger.info(
                    f"Generated group {len(groups)}: {seed.name} + "
                    f"{len(group['equipments']) - 1} companions"
                )

        logger.info(f"Generated {len(groups)}/{count} random groups")
        return groups
