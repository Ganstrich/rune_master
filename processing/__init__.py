"""Processing layer for equipment group discovery.

The greedy grouping expert (``RuneMaster``) discovers equipment groups.
Submodules:

- ``experts``   — the greedy grouping expert behind ``GroupingExpert``
- ``filters``   — pool filters applied once, before the expert runs
- ``metrics``   — group/portfolio metrics and the run reporter
- ``valuation`` — swappable group objectives and their inputs
- ``blocks``    — pure recipe/similarity/shopping-list helpers
- ``tools``     — offline comparison and tuning (not the runtime pipeline)
"""

from processing.config import ProcessingConfig
from processing.orchestrator import RuneMaster
from processing.metrics.group_metrics import GroupMetrics
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
    "GroupMetrics",
    "GroupQualityEvaluator",
    "GroupQualityMetrics",
    "GroupQualityWeights",
    "PortfolioQualityEvaluator",
    "PortfolioQualityMetrics",
    "PortfolioQualityWeights",
]
