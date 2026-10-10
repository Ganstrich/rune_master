"""Configuration for the processing pipeline.

GROUPING METHOD SELECTION:
    The grouping_method field determines which algorithm discovers equipment groups.
    
    Performance and quality trade-offs (measured, 2026-10-10):
    - "deterministic": 0.1-2.1s, PQ 0.23-0.43, cov 29-53% (graph-based, full coverage)
    - "random": 0.0-0.1s, PQ 0.04-0.25, cov 7-25% (stochastic sampling, baseline)
    - "hybrid": 0.1-2.0s, PQ 0.00-0.41, cov 37-55% (deterministic + random fallback)
    - "greedy": 0.4-8.5s, PQ 0.34-0.58, cov 29-82% (objective-driven, full pool) ← DEFAULT
    
    RECOMMENDATION: Use "greedy" (default) for best quality/coverage/speed.
    Use "deterministic" for development. Use "random" for baseline comparison.
"""
from dataclasses import dataclass, field
from typing import Optional

from processing.metrics.quality_metrics import GroupQualityWeights, PortfolioQualityWeights

@dataclass
class ProcessingConfig:
    """Configuration for RuneMaster processing pipeline."""

    # Graph building
    # 0.3 left 408 of 2858 items (14.28%) with no edge at all, spanning all 17
    # slots and all 11 bands; 405 of those still share >=1 resource with the
    # pool and are therefore groupable. 0.15 lifts reachability to 99.37%.
    # The policy's efficiency floor absorbs the precision cost (metrics-revision §3.1).
    graph_min_shared_ratio: float = 0.15
    graph_min_shared_count: int = (
        1  # Min absolute shared resources for edge (independent of ratio)
    )
    graph_min_component_size: int = 2  # MIN_CLUSTER_SIZE
    # Damps edges between items of the same panoplie so Louvain stops
    # rediscovering sets as communities. 1.0 disables the correction.
    same_set_edge_discount: float = 1.0

    # Greedy objective-driven expert
    greedy_candidate_limit: int = 25  # Candidates scored per growth step
    greedy_seed_limit: int = 0  # Seeds to expand; zero uses the whole pool

    # Community detection
    algorithm: str = "louvain"  # "louvain", "bilouvain", or "none"
    resolution_range: tuple = (1, 10, 1)

    # Group mapping
    group_min_size: int = 2
    group_max_size: int = 12  # Reachable at max_line_items=32; 32 admitted groups that could never pass.
    group_min_shared_resources: int = 3
    group_efficiency_threshold: float = 0.15
    group_quality_threshold: float = 0.0
    # Hard cap on the share of a group that may come from one panoplie.
    group_max_set_share: float = 0.5
    # C2: groups must not be built from panoplie items. Items belonging to a set
    # of at least this many members are dropped from the candidate pool before
    # any expert runs, because set items are the over-crafted low-taux choices.
    # Set to 99 to disable. 5 is the data-backed default: it removes 494 items
    # (17.28%) whose median stat_weight is 82.5 vs 298.1 retained, while the
    # retained pool still reaches 99.24% coverage (metrics-revision §3.8).
    set_exclusion_min_size: int = 5
    max_line_items: int = 32  # Union cap; binds shopping effort. 12 discarded 95% of buildable groups (data-profile §3.2).
    max_total_units: int = 2000  # Secondary to line items; 500 rejected 43% of buildable groups.
    acquisition_cost: float = 0.0  # Kama-equivalent effort per distinct resource.
    flat_taux: float = 1.0  # Theoretical placeholder until break outcomes are logged.
    price_max_age_seconds: float = 3600.0
    group_quality_weights: GroupQualityWeights = field(default_factory=GroupQualityWeights)
    use_inclusive_mapping: bool = False

    # Excluded resources (won't count toward sharing efficiency).
    # 15263 was removed: absent from the resources table and referenced by zero
    # recipe entries of any subtype in snapshot 3.7.7.6 (metrics-revision §3.5).
    excluded_resource_ids: set = field(default_factory=lambda: {14635})

    # Density/Level filtering
    use_density_filtering: bool = True
    equipment_density_level_ratio: float = 2.0  # 3.0 kept only 40.90% of items; 2.0 keeps 72.15% (metrics-revision §3.4)
    fallback_to_unfiltered: bool = False  # FALLBACK_TO_UNFILTERED
    min_filtered_pool_size: int = 10  # MIN_FILTERED_POOL_SIZE

    # Grouping method
    grouping_method: str = "greedy"  # "deterministic", "random", "hybrid", "greedy", "survey"
    random_group_count: int = 50
    random_seed: Optional[int] = None

    # Equipment pre-filtering
    min_equipment_density: float = 0.0  # Minimum stat_weight per level (0 = no filter)
    density_percentile: float = 0.0  # Within-level-band percentile; zero disables the gate.
    density_level_band: int = 20  # Level width used for percentile bands.

    # MoE De-duplication
    dedup_overlap_threshold: float = (
        0.7  # Jaccard similarity threshold for considering groups as duplicates
    )
    portfolio_quality_weights: PortfolioQualityWeights = field(
        default_factory=PortfolioQualityWeights
    )

    # Job-level filtering (craftability by player profession levels)
    # use_job_level_filter=False keeps the whole pool (default behavior).
    # When True and job_levels is populated, equipment whose crafting job is
    # below the item level is dropped before any expert runs.
    use_job_level_filter: bool = False
    job_levels: dict = field(default_factory=dict)
