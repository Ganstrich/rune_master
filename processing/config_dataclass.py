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
    group_min_size: int = 2  # MIN_CLUSTER_SIZE
    group_max_size: int = 18
    group_min_shared_resources: int = 3  # MIN_COMMON_ITEMS
    group_efficiency_threshold: float = 0.15
    use_inclusive_mapping: bool = False

    # Excluded resources (won't count toward sharing efficiency)
    excluded_resource_ids: set = field(
        default_factory=lambda: {15263, 14635}
    )  # EXCLUDED_RESOURCES

    # Density/Level filtering
    use_density_filtering: bool = True
    equipment_density_level_ratio: float = 0.15  # DENSITY_LEVEL_RATIO
    fallback_to_unfiltered: bool = True  # FALLBACK_TO_UNFILTERED
    min_filtered_pool_size: int = 10  # MIN_FILTERED_POOL_SIZE

    # Grouping method
    grouping_method: str = (
        "hybrid"  # "deterministic", "random", "hybrid", "committee", "genetic"
    )
    random_group_count: int = 50  # RANDOM_GROUP_COUNT
    random_seed: Optional[int] = None

    # Equipment pre-filtering
    min_equipment_density: float = 0.0  # Minimum stat_weight per level (0 = no filter)

    # MoE De-duplication
    dedup_overlap_threshold: float = (
        0.7  # Jaccard similarity threshold for considering groups as duplicates
    )
