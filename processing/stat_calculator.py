"""Equipment stat weight calculation engine.

Responsible for:
- Calculating individual stat line weights based on min/max values and stat type weights
- Computing overall equipment weight from all stat lines
- Handling static stat weight mappings (Vitalité, Sagesse, etc.)
- Resilient stat name matching to handle API inconsistencies

Stat Weight Formula:
    stat_line_weight = avg(min, max) * weight[stat_type]
    where only positive averages are counted
    
    equipment_weight = sum(stat_line_weight for all stats where avg > 0)

Stat Name Resilience:
The system handles API inconsistencies in stat naming through multiple strategies:

1. resolve_stat_name():
    - Attempts exact match first
    - Falls back to case-insensitive matching
    - Uses fuzzy matching to handle singular/plural variations
    - Normalizes "Dommage" ↔ "Dommages", "Résistance" ↔ "Résistances", etc.

2. STAT_WEIGHTS includes both singular and plural variants:
   - Each stat has entries for common variations
   - Example: "Dommage" and "Dommages" both map to weight 5
   - Makes matching robust without needing to infer IDs

3. Error handling with helpful suggestions:
   - If stat is unknown, suggests similar stats
   - Provides list of available stats for debugging
   - Continues calculation, marking unknown stats as warnings

This approach eliminates the need for manually maintaining stat ID mappings,
since we match on stat names instead.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from models import Equipment
from processing.valuation.density import RUNE_DENSITY, resolve_stat_name


# ============================================================================
# STAT WEIGHTS - Static configuration table
# ============================================================================
# Map stat names to their weights in the calculation
# These weights represent the importance/value of each stat type
# Values to be completed by user

STAT_WEIGHTS: Dict[str, float] = RUNE_DENSITY
"""Backward-compatible name for the valuation-layer density table."""


# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def calculate_stat_line_weight(
    stat_type: str,
    min_value: float,
    max_value: float,
    stat_weights: Optional[Dict[str, float]] = None
) -> float:
    """Calculate weight for a single stat line.
    
    Formula:
        If avg(min, max) > 0:
            weight = avg(min, max) * stat_weight[stat_type]
        Else:
            weight = 0 (ignored)
    
    Args:
        stat_type: Name of the stat (e.g., "Vitalité", "Sagesse")
        min_value: Minimum value of the stat
        max_value: Maximum value of the stat
        stat_weights: Optional override of STAT_WEIGHTS mapping
        
    Returns:
        Weight contribution of this stat line (0 if avg ≤ 0)
        
    Raises:
        KeyError: If stat_type not found in stat_weights (after fuzzy matching)
    """
    weights = stat_weights or STAT_WEIGHTS
    
    stat_type = resolve_stat_name(stat_type, weights)
    
    # Calculate average
    avg = (min_value + max_value) / 2.0
    
    # Only count positive averages
    if avg <= 0:
        return 0.0
    
    # Return weighted average
    stat_weight = weights[stat_type]
    return avg * stat_weight


def calculate_equipment_weight(
    equipment: Equipment,
    stat_weights: Optional[Dict[str, float]] = None
) -> float:
    """Calculate total weight of an equipment from all stats.
    
    Args:
        equipment: Equipment dataclass with effects
        stat_weights: Optional override of STAT_WEIGHTS mapping
        
    Returns:
        Total equipment weight (sum of all valid stat line weights)
    """
    weights = stat_weights or STAT_WEIGHTS
    total_weight = 0.0
    
    # Iterate through all stats/effects on this equipment
    for stat in equipment.effects:
        try:
            # Extract stat name from EquipmentStat.stat_type dict
            stat_name = stat.stat_name  # Uses the @property from EquipmentStat
            stat_line_weight = calculate_stat_line_weight(
                stat_type=stat_name,
                min_value=stat.int_minimum,
                max_value=stat.int_maximum,
                stat_weights=weights
            )
            total_weight += stat_line_weight
        except (KeyError, AttributeError) as e:
            # Log unknown stat types but continue calculation
            print(f"⚠️  Skipping stat for equipment {equipment.name}: {e}")
            continue
    
    return total_weight


def calculate_equipment_weights_batch(
    equipments: list,
    stat_weights: Optional[Dict[str, float]] = None
) -> Dict[int, float]:
    """Calculate weights for multiple equipment.
    
    Args:
        equipments: List of Equipment dataclasses
        stat_weights: Optional override of STAT_WEIGHTS mapping
        
    Returns:
        Dict mapping equipment ankama_id to weight
    """
    weights = stat_weights or STAT_WEIGHTS
    result = {}
    
    for equipment in equipments:
        weight = calculate_equipment_weight(equipment, weights)
        result[int(equipment.ankama_id)] = weight
    
    return result


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_stat_weights(stat_weights: Dict[str, float]) -> bool:
    """Validate that stat weights are properly configured.
    
    Args:
        stat_weights: Dict of stat_type → weight
        
    Returns:
        True if valid, raises ValueError otherwise
    """
    if not stat_weights:
        raise ValueError("Stat weights dictionary is empty")
    
    for stat_type, weight in stat_weights.items():
        if not isinstance(stat_type, str):
            raise ValueError(f"Stat type must be string, got {type(stat_type)}")
        if not isinstance(weight, (int, float)):
            raise ValueError(f"Weight must be numeric, got {type(weight)} for {stat_type}")
        if weight < 0:
            raise ValueError(f"Weight must be non-negative, got {weight} for {stat_type}")
    
    return True


def get_stat_weights_summary(stat_weights: Optional[Dict[str, float]] = None) -> str:
    """Get human-readable summary of stat weights.
    
    Args:
        stat_weights: Optional override of STAT_WEIGHTS
        
    Returns:
        Formatted string summarizing the weights
    """
    weights = stat_weights or STAT_WEIGHTS
    
    if not weights:
        return "No stat weights configured"
    
    lines = ["Stat Weight Configuration:"]
    for stat_type in sorted(weights.keys()):
        lines.append(f"  {stat_type}: {weights[stat_type]}")
    
    return "\n".join(lines)


# ============================================================================
# INITIALIZATION
# ============================================================================

# TODO: Complete STAT_WEIGHTS with actual values from the static table
# Example structure:
# STAT_WEIGHTS = {
#     "Vitalité": 0.5,
#     "Sagesse": 0.3,
#     "Intelligence": 0.8,
#     "Force": 0.7,
#     "Agilité": 0.6,
#     "Chance": 0.4,
# }
