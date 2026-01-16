"""Processing module: Graph building, community detection, and group mapping.

Main entry point is RuneMaster orchestrator which coordinates the full pipeline.

Example usage:
    from processing import RuneMaster, ProcessingConfig
    from data import EquipmentLoader

    # Load equipment
    loader = EquipmentLoader()
    equipments = loader.from_raw_batch(raw_data)

    # Configure and run pipeline
    config = ProcessingConfig(
        algorithm="louvain",
        group_efficiency_threshold=0.15
    )
    master = RuneMaster(equipments, config=config)
    groups = master.run_all()
    master.print_summary()
"""

from processing.orchestrator import RuneMaster, ProcessingConfig
from processing.graph_builder import GraphBuilder
from processing.community_detector import CommunityDetector
from processing.group_mapper import GroupMapper

__all__ = [
    "RuneMaster",
    "ProcessingConfig",
    "GraphBuilder",
    "CommunityDetector",
    "GroupMapper",
]
