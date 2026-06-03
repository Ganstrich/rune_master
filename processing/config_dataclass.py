"""Configuration for the processing pipeline."""
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ProcessingConfig:
    """Configuration for RuneMaster processing pipeline."""

    # Graph building
    graph_min_shared_ratio: float = 0.2
    graph_min_component_size: int = 2

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
    equipment_density_level_ratio: float = 0.15
    fallback_to_unfiltered: bool = True
    min_filtered_pool_size: int = 10

    # Grouping method
    grouping_method: str = "deterministic"  # "deterministic", "random", "hybrid", "committee"
    random_group_count: int = 10
    random_seed: Optional[int] = None
