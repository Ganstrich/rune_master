"""Processing layer for equipment group discovery.

Contains algorithms for graph building, community detection, 
group mapping, and the Mixture of Experts (MoE) orchestrator.
"""

from processing.config_dataclass import ProcessingConfig
from processing.orchestrator import RuneMaster
from processing.graph_builder import GraphBuilder
from processing.community_detector import CommunityDetector
from processing.group_mapper import GroupMapper
from processing.group_metrics import GroupMetrics
from processing.random_group_builder import RandomGroupBuilder
from processing.quality_metrics import (
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
