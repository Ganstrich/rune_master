"""Common type definitions for models."""
from typing import TypedDict
from enum import Enum


class ImageURLs(TypedDict):
    """Image URL references for items."""
    icon: str
    sd: str


class ItemType(TypedDict):
    """Item type metadata."""
    name: str
    id: int


class StatType(TypedDict):
    """Stat type metadata."""
    name: str
    id: int


# ============================================================================
# STAT MAPPINGS - Read-only reference data
# ============================================================================

STAT_ID_TO_NAME = {
    9: 'Vitalité',
    10: 'Sagesse',
    25: 'Prospection',
    29: '% Critique',
    38: 'Dommage Critiques',
    59: 'Fuite',
    121: 'Soin',
    63: '% Résistance Terre',
    17: '% Résistance Eau',
    16: '% Résistance Air',
    31: 'Portée',
    46: 'Résistance Critiques',
}

STAT_NAME_TO_ID = {v: k for k, v in STAT_ID_TO_NAME.items()}


# ============================================================================
# STAT WEIGHT ENUM - For scoring importance of stats
# ============================================================================

class StatWeight(Enum):
    """Relative importance/weight of each stat for scoring purposes."""
    PA = 100.0
    PM = 90.0
    Portée = 51.0
    Invocation = 30.0
    Dommage = 20.0
    Vitalité = 0.2
    Pods = 0.25
    Initiative = 0.1
    Force = 1.0
    Intelligence = 1.0
    Chance = 1.0
    Agilité = 1.0
    Sagesse = 3.0
    Prospection = 0.5
    
    @classmethod
    def get_weight(cls, stat_name: str) -> float:
        """Get weight for a stat by name, default to 1.0 if not found."""
        try:
            return cls[stat_name].value
        except KeyError:
            return 1.0