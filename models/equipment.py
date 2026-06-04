"""Equipment data model."""

from dataclasses import dataclass, field
from typing import TypedDict, Dict, Any, Optional, List

from .common import ImageURLs, ItemType, StatType
from .recipe import ResourceRequirement


class EquipmentStat:
    """Represents an equipment effect/stat with all metadata from API.

    Pure data container - no business logic.
    """

    def __init__(
        self,
        stat_type: StatType,
        int_minimum: int,
        int_maximum: int,
        ignore_int_min: bool = False,
        ignore_int_max: bool = False,
        formatted: str = "",
    ):
        self.stat_type = stat_type
        self.int_minimum = int_minimum
        self.int_maximum = int_maximum
        self.ignore_int_min = ignore_int_min
        self.ignore_int_max = ignore_int_max
        self.formatted = formatted

    @property
    def stat_name(self) -> str:
        """Get the stat name, normalized to match STAT_WEIGHTS keys.

        Handles:
        - Case normalization (e.g., "eau" vs "Eau")
        - Singular/plural variations (e.g., "Dommage" vs "Dommages")
        - Common API inconsistencies

        Uses fuzzy matching to find the best STAT_WEIGHTS key.
        """
        from processing.stat_calculator import STAT_WEIGHTS

        raw_name = self.stat_type["name"]

        # First, try exact match (most common case)
        if raw_name in STAT_WEIGHTS:
            return raw_name

        # Try case-insensitive exact match
        for key in STAT_WEIGHTS.keys():
            if key.lower() == raw_name.lower():
                return key

        # Try fuzzy matching: normalize singular/plural
        # Convert to a canonical form for comparison
        def normalize_for_matching(s: str) -> list:
            """Normalize string for fuzzy matching."""
            # Remove common plural endings
            s_lower = s.lower()

            # Try removing 's' at the end (works for most French plurals)
            variants = [s_lower]
            if s_lower.endswith("s"):
                variants.append(s_lower[:-1])  # Remove trailing 's'
            if s_lower.endswith("es"):
                variants.append(s_lower[:-2])  # Remove 'es'

            return variants

        raw_variants = normalize_for_matching(raw_name)

        # Find matching key by checking if any variant matches any key variant
        for key in STAT_WEIGHTS.keys():
            key_variants = normalize_for_matching(key)

            # Check if any variant of raw_name matches any variant of key
            for raw_var in raw_variants:
                for key_var in key_variants:
                    if raw_var == key_var:
                        return key  # Return the canonical STAT_WEIGHTS key

        # If no fuzzy match found, return original (will cause KeyError in calculator)
        # This preserves the current behavior for debugging unknown stats
        return raw_name

    @property
    def stat_id(self) -> int:
        """Get the stat id."""
        return self.stat_type["id"]

    def __repr__(self) -> str:
        return (
            f"EquipmentStat(name={self.stat_name}, "
            f"min={self.int_minimum}, max={self.int_maximum})"
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, EquipmentStat):
            return False
        return (
            self.stat_type == other.stat_type
            and self.int_minimum == other.int_minimum
            and self.int_maximum == other.int_maximum
        )


@dataclass(frozen=False)
class Equipment:
    """Equipment data model.

    Pure data container - no API calls, no transformations.
    All business logic (loading, stat weight calculation) goes to loaders.py

    NOTE: NOT frozen to allow loaders to set all fields after creation.
    """

    ankama_id: int
    type: ItemType
    level: int
    name: str
    effects: List[EquipmentStat] = field(default_factory=list)
    stat_weight: Optional[float] = None
    recipe: List[ResourceRequirement] = field(default_factory=list)
    image_urls: Optional[ImageURLs] = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if self.ankama_id < 0:
            raise ValueError(f"ankama_id must be positive, got {self.ankama_id}")
        if self.level < 0:
            raise ValueError(f"level must be positive, got {self.level}")

    def __hash__(self) -> int:
        """Make Equipment hashable by its unique ID."""
        return hash(self.ankama_id)

    def __eq__(self, other: Any) -> bool:
        """Equality based on unique ID."""
        if not isinstance(other, Equipment):
            return False
        return self.ankama_id == other.ankama_id

    def total_pods_needed(self) -> int:
        """Calculate total pods needed for this equipment's recipe.

        NOTE: This is a simple getter - it doesn't fetch resource data.
        Use loaders.py if you need to look up resource pod weights.
        """
        # This would need additional data to compute properly
        # For now, it's a placeholder for future enhancement
        return 0

    def __repr__(self) -> str:
        effects_str = f"{len(self.effects)} effects" if self.effects else "no effects"
        recipe_str = f"{len(self.recipe)} items" if self.recipe else "no recipe"
        return (
            f"Equipment("
            f"id={self.ankama_id}, "
            f"name={self.name}, "
            f"level={self.level}, "
            f"{effects_str}, "
            f"{recipe_str})"
        )
