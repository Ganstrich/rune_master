"""Configuration for the processing pipeline.

The greedy grouping expert is the single production method.
"""
from dataclasses import dataclass, field

from processing.metrics.quality_metrics import GroupQualityWeights, PortfolioQualityWeights

@dataclass
class ProcessingConfig:
    """Configuration for RuneMaster processing pipeline."""

    # -- Pipeline ----------------------------------------------------------
    grouping_method: str = "greedy"

    # -- Experts -----------------------------------------------------------
    greedy_candidate_limit: int = 25  # Candidates scored per growth step
    greedy_seed_limit: int = 0  # Seeds to expand; zero uses the whole pool

    # -- Filters (applied once, before the expert runs) ---------------------
    use_density_filtering: bool = True
    equipment_density_level_ratio: float = 2.0
    fallback_to_unfiltered: bool = False
    min_filtered_pool_size: int = 10
    min_equipment_density: float = 0.0
    density_percentile: float = 0.0
    density_level_band: int = 20
    set_exclusion_min_size: int = 5
    excluded_resource_ids: set = field(default_factory=lambda: {14635})
    use_job_level_filter: bool = False
    job_levels: dict = field(default_factory=dict)

    # -- Group acceptance (policy) -----------------------------------------
    group_min_size: int = 2
    group_max_size: int = 12
    group_min_shared_resources: int = 3
    group_efficiency_threshold: float = 0.15
    group_quality_threshold: float = 0.0
    group_max_set_share: float = 0.5
    max_line_items: int = 32
    max_total_units: int = 2000

    # -- Objective / valuation ---------------------------------------------
    acquisition_cost: float = 0.0
    flat_taux: float = 1.0
    price_max_age_seconds: float = 3600.0
    group_quality_weights: GroupQualityWeights = field(default_factory=GroupQualityWeights)

    # -- Metrics -----------------------------------------------------------
    portfolio_quality_weights: PortfolioQualityWeights = field(
        default_factory=PortfolioQualityWeights
    )
