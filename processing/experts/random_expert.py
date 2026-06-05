"""Random-based grouping expert using stochastic selection."""
from typing import List, Dict, Any, Optional, Set
from models import Equipment
from processing.experts.base import GroupingExpert
from processing.config_dataclass import ProcessingConfig
from processing.equipment_filter import EquipmentFilteringStrategy
from processing.random_group_builder import RandomGroupBuilder

class RandomGroupingExpert(GroupingExpert):
    """Expert that uses random selection and density filtering to find groups.
    
    Useful for supplementing deterministic methods or finding non-obvious clusters.
    """
    
    def __init__(
        self, 
        cache_manager: Optional[Any] = None,
        api_client: Optional[Any] = None
    ):
        super().__init__("RandomExpert", cache_manager, api_client)

    def discover_groups(
        self, 
        equipments: List[Equipment], 
        config: ProcessingConfig,
        precomputed_graph: Optional[Any] = None,
        precomputed_resources: Optional[Dict[int, Set[int]]] = None,
    ) -> List[Dict[str, Any]]:
        """Run the random-based discovery pipeline."""
        print(f"      [{self.name}] Filtering pool and generating random groups...")
        
        # 1. Get active pool (possibly filtered)
        active_pool, was_filtered = EquipmentFilteringStrategy.get_active_pool(
            equipments,
            use_filtering=config.use_density_filtering,
            density_ratio=config.equipment_density_level_ratio,
            fallback_to_unfiltered=config.fallback_to_unfiltered,
            min_pool_size=config.min_filtered_pool_size,
        )

        filter_status = "filtered" if was_filtered else "unfiltered"
        print(f"      [{self.name}] Active pool: {len(active_pool)} equipment ({filter_status})")

        # 2. Build random groups
        builder = RandomGroupBuilder(
            equipments,
            excluded_resource_ids=config.excluded_resource_ids,
            seed=config.random_seed,
            cache_manager=self.cache_manager,
        )

        groups = builder.build_multiple_random_groups(
            active_pool,
            count=config.random_group_count,
            min_shared_resources=config.group_min_shared_resources,
            max_group_size=config.group_max_size,
            avoid_seed_duplicates=True,
        )

        # Add metadata
        for group in groups:
            group["expert_name"] = self.name
            # selection_method is already set to "random" by RandomGroupBuilder
            
        return groups
