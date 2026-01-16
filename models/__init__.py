"""Models package - Clean data structures with no business logic.

All transformations (from_raw, API calls, calculations) go to data/loaders.py
"""

# Type definitions and enums
from .common import (
    ImageURLs,
    ItemType,
    StatType,
    StatWeight,
    STAT_ID_TO_NAME,
    STAT_NAME_TO_ID,
)

# Data models
from .equipment import Equipment, EquipmentStat
from .resource import Resource
from .recipe import ResourceRequirement

__all__ = [
    # Type definitions
    "ImageURLs",
    "ItemType",
    "StatType",
    "StatWeight",
    "STAT_ID_TO_NAME",
    "STAT_NAME_TO_ID",
    # Models
    "Equipment",
    "EquipmentStat",
    "Resource",
    "ResourceRequirement",
]
