"""Configuration for the processing pipeline."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProcessingConfig:
    """Configuration for RuneMaster processing pipeline."""

    # Graph building
    graph_min_shared_ratio: float = 0.3
    graph_min_shared_count: int = (
        1  # Min absolute shared resources for edge (independent of ratio)
    )
    graph_min_component_size: int = 2  # MIN_CLUSTER_SIZE

    # Community detection
    algorithm: str = "louvain"  # "louvain", "bilouvain", or "none"
    resolution_range: tuple = (1, 10, 1)

    # Group mapping
    group_min_size: int = 2
    group_max_size: int = 18
    group_min_shared_resources: int = 2
    group_efficiency_threshold: float = 0.15
    use_inclusive_mapping: bool = False

    # Optimization
    use_resource_optimizer: bool = True

    # Excluded resources (won't count toward sharing efficiency)
    excluded_resource_ids: set = field(default_factory=set)

    # Density/Level filtering
    use_density_filtering: bool = True
    equipment_density_level_ratio: float = 0.15  # DENSITY_LEVEL_RATIO
    fallback_to_unfiltered: bool = True  # FALLBACK_TO_UNFILTERED
    min_filtered_pool_size: int = 10  # MIN_FILTERED_POOL_SIZE

    # Grouping method
    grouping_method: str = (
        "deterministic"  # "deterministic", "random", "hybrid", "committee"
    )
    random_group_count: int = 10
    random_seed: Optional[int] = None

    # Equipment pre-filtering
    min_equipment_density: float = 0.0  # Minimum stat_weight per level (0 = no filter)

    @classmethod
    def from_args(cls, args, config_defaults):
        return cls(
            graph_min_shared_ratio=config_defaults.MIN_SIMILARITY,
            graph_min_component_size=config_defaults.MIN_CLUSTER_SIZE,
            algorithm="louvain",
            resolution_range=(1, 10, 1),
            group_min_size=config_defaults.MIN_CLUSTER_SIZE,
            group_max_size=18,
            group_min_shared_resources=config_defaults.MIN_COMMON_ITEMS,
            group_efficiency_threshold=0.15,
            use_inclusive_mapping=False,
            use_resource_optimizer=False,
            excluded_resource_ids=set(config_defaults.EXCLUDED_RESOURCES or []),
            use_density_filtering=True,
            equipment_density_level_ratio=args.density_ratio
            or config_defaults.DENSITY_LEVEL_RATIO,
            fallback_to_unfiltered=config_defaults.FALLBACK_TO_UNFILTERED,
            min_filtered_pool_size=config_defaults.MIN_FILTERED_POOL_SIZE,
            grouping_method=args.grouping_method or config_defaults.GROUPING_METHOD,
            random_group_count=args.random_groups or config_defaults.RANDOM_GROUP_COUNT,
            random_seed=None,
            min_equipment_density=config_defaults.MIN_EQUIPMENT_DENSITY,
        )
