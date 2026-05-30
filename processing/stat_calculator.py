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

1. EquipmentStat.stat_name property:
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


# ============================================================================
# STAT WEIGHTS - Static configuration table
# ============================================================================
# Map stat names to their weights in the calculation
# These weights represent the importance/value of each stat type
# Values to be completed by user

STAT_WEIGHTS: Dict[str, float] = {
    # Stats like "Vitalité", "Sagesse", etc.
    # Format: "stat_name": weight_value
    # Example:
    # "Vitalité": 0.5,
    # "Sagesse": 0.3,
    # "Intelligence": 0.8,
    "PA": 100,
    "PM": 90,
    "Portée": 51,
    "Invocation": 30,
    "Dommage": 5,
    "Dommages": 5,  # Plural variant
    "Dommage Terre": 5,
    "Dommages Terre": 5,  # Plural variant
    "Dommage Feu": 5,
    "Dommages Feu": 5,  # Plural variant
    "Dommage Eau": 5,
    "Dommages Eau": 5,  # Plural variant
    "Dommage Air": 5,
    "Dommages Air": 5,  # Plural variant
    "Dommage Neutre": 5,
    "Dommages Neutre": 5,  # Plural variant
    "Dommage Critiques": 5,
    "Dommages Critiques": 5,  # Plural variant
    "Dommages poussée": 5,
    "Dommage poussée": 5,  # Singular variant
    "Dommage Pièges": 5,
    "Dommages Pièges": 5,  # Plural variant
    "% Résistance terre": 6,
    "% Résistances terre": 6,  # Plural variant
    "% Résistance feu": 6,
    "% Résistances feu": 6,  # Plural variant
    "% Résistance eau": 6,
    "% Résistances eau": 6,  # Plural variant
    "% Résistance air": 6,
    "% Résistances air": 6,  # Plural variant
    "% Résistance neutre": 6,
    "% Résistances neutre": 6,  # Plural variant
    "Retrait PA": 7,
    "Retraits PA": 7,  # Plural variant
    "Retrait PM": 7,
    "Retraits PM": 7,  # Plural variant
    "Esquive PA": 7,
    "Esquives PA": 7,  # Plural variant
    "Esquive PM": 7,
    "Esquives PM": 7,  # Plural variant
    "% Critique": 10,
    "% Critiques": 10,  # Plural variant
    "Soin": 10,
    "Soins": 10,  # Plural variant
    "Renvoi dommages": 10,
    "Renvois dommages": 10,  # Plural variant
    "Tacle": 4,
    "Tacles": 4,  # Plural variant
    "Fuite": 4,
    "Fuites": 4,  # Plural variant
    "Sagesse": 3,
    "Prospection": 3,
    "Puissance": 2,
    "Résistance Terre": 2,
    "Résistances Terre": 2,  # Plural variant
    "Résistance Feu": 2,
    "Résistances Feu": 2,  # Plural variant
    "Résistance Eau": 2,
    "Résistances Eau": 2,  # Plural variant
    "Résistance Air": 2,
    "Résistances Air": 2,  # Plural variant
    "Résistance Neutre": 2,
    "Résistances Neutre": 2,  # Plural variant
    "Résistance Critiques": 2,
    "Résistances Critiques": 2,  # Plural variant
    "Résistance Poussée": 2,
    "Résistances Poussée": 2,  # Plural variant
    "Force": 1,
    "Intelligence": 1,
    "Agilité": 1,
    "Chance": 1,
    "Vitalité": 0.2,
    "Pod": 0.25,
    "Initiative": 0.1,
}


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
    
    if stat_type not in weights:
        # Try to find a close match with case-insensitive search
        for key in weights.keys():
            if key.lower() == stat_type.lower():
                stat_type = key
                break
        else:
            # Still not found - provide helpful error message
            similar = [k for k in weights.keys() if k.lower().startswith(stat_type.lower()[:3])]
            raise KeyError(
                f"Unknown stat type: '{stat_type}'. "
                f"Did you mean: {similar if similar else 'See available stats below'}? "
                f"Available: {list(weights.keys())}"
            )
    
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
