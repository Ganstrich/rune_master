"""Processing layer for equipment group discovery.

The MoE orchestrator (``RuneMaster``) coordinates the grouping experts over a
shared equipment graph. Submodules:

- ``graph``     — graph construction, community detection, group mapping
- ``experts``   — one grouping algorithm per expert, behind ``GroupingExpert``
- ``filters``   — pool filters applied once, before any expert runs
- ``metrics``   — group/portfolio metrics and the run reporter
- ``valuation`` — swappable group objectives and their inputs
- ``blocks``    — pure recipe/similarity/shopping-list helpers
- ``tools``     — offline comparison and tuning (not the runtime pipeline)
"""

from processing.config import ProcessingConfig
from processing.orchestrator import RuneMaster
from processing.graph.graph_builder import GraphBuilder
from processing.graph.community_detector import CommunityDetector
from processing.graph.group_mapper import GroupMapper
from processing.metrics.group_metrics import GroupMetrics
from processing.experts.random_group_builder import RandomGroupBuilder
from processing.metrics.quality_metrics import (
    GroupQualityEvaluator,
    GroupQualityMetrics,
    GroupQualityWeights,
    PortfolioQualityEvaluator,
    PortfolioQualityMetrics,
    PortfolioQualityWeights,
)
__all__ = [
    "ProcessingConfig",
    "RuneMaster",
    "GraphBuilder",
    "CommunityDetector",
    "GroupMapper",
    "GroupMetrics",
    "RandomGroupBuilder",
    "GroupQualityEvaluator",
    "GroupQualityMetrics",
    "GroupQualityWeights",
    "PortfolioQualityEvaluator",
    "PortfolioQualityMetrics",
    "PortfolioQualityWeights",
]
