"""Equipment filtering by density/level ratio.

Provides filtering strategies to reduce equipment pool based on stat density
(stat_weight per level). Used for both random grouping and exploration.
"""

import logging
from collections import defaultdict
from typing import List, Optional
from models import Equipment

logger = logging.getLogger(__name__)


class EquipmentFilteringStrategy:
    """Filters equipment pool based on density/level ratio.
    
    Density ratio = stat_weight / level
    Higher density indicates more powerful equipment at a given level.
    """

    @staticmethod
    def calculate_minimum_density(level: int, ratio: float) -> float:
        """Calculate minimum stat_weight needed for given level and ratio.
        
        Args:
            level: Equipment level
            ratio: Density ratio (e.g., 0.15 = 15% of level)
            
        Returns:
            Minimum stat_weight for this equipment to pass filter
            
        Example:
            >>> calculate_minimum_density(100, 0.15)
            15.0
        """
        return level * ratio

    @staticmethod
    def filter_by_density_ratio(
        equipments: List[Equipment],
        ratio: float
    ) -> tuple:
        """Filter equipment by density/level ratio.
        
        Keeps only equipment where stat_weight >= level * ratio.
        Equipment with None stat_weight are excluded.
        
        Args:
            equipments: List of all Equipment objects
            ratio: Density ratio threshold (e.g., 0.15)
            
        Returns:
            Tuple of (filtered_equipments, excluded_equipments)
        """
        if ratio <= 0:
            return equipments, []

        filtered = []
        excluded = []

        for eq in equipments:
            # Skip equipment without stat_weight
            if eq.stat_weight is None:
                excluded.append(eq)
                continue

            min_density = EquipmentFilteringStrategy.calculate_minimum_density(
                eq.level, ratio
            )

            if eq.stat_weight >= min_density:
                filtered.append(eq)
            else:
                excluded.append(eq)

        return filtered, excluded

    @staticmethod
    def get_active_pool(
        equipments: List[Equipment],
        use_filtering: bool = True,
        density_ratio: float = 0.15,
        fallback_to_unfiltered: bool = True,
        min_pool_size: int = 10,
    ) -> tuple:
        """Get the active equipment pool based on filtering strategy.

        Args:
            equipments: List of all Equipment objects
            use_filtering: Whether to apply density filtering
            density_ratio: Density threshold if filtering enabled
            fallback_to_unfiltered: Fall back to unfiltered if filtered pool too small
            min_pool_size: Minimum pool size before triggering fallback

        Returns:
            Tuple of (active_pool, was_filtered)
            - active_pool: Equipment list to use for processing
            - was_filtered: Boolean indicating if filtering was applied
        """
        if not use_filtering:
            return equipments, False

        filtered, excluded = EquipmentFilteringStrategy.filter_by_density_ratio(
            equipments, density_ratio
        )

        logger.info(
            f"Filtered pool: {len(filtered)} / {len(equipments)} equipment "
            f"(density ratio >= {density_ratio:.2f})"
        )

        # Check if filtered pool is too small
        if len(filtered) < min_pool_size and fallback_to_unfiltered:
            logger.warning(
                f"Filtered pool too small ({len(filtered)} < {min_pool_size}). "
                f"Falling back to unfiltered pool ({len(equipments)} items)."
            )
            return equipments, False

        return filtered, True


class SetExclusionFilter:
    """Drop panoplie items from the candidate pool (constraint C2).

    Groups must not be built from set items: items belonging to a panoplie of
    at least ``min_set_size`` members are systematically over-crafted and break
    at low taux. Enforcing this at pool level — rather than as a score term —
    keeps ``set_free_ratio`` free to reward setless items instead of merely
    cancelling a penalty.
    """

    @staticmethod
    def summarize_set_sizes(equipments: List[Equipment]) -> dict[int, int]:
        """Return a ``set_id -> member count`` map for the whole pool.

        Set membership is only knowable relative to the pool being filtered, so
        the count is computed from the supplied list rather than from a global
        index.
        """
        members: dict[int, int] = {}
        for equipment in equipments:
            set_id = getattr(equipment, "set_id", None)
            if set_id is None:
                continue
            set_id = int(set_id)
            members[set_id] = members.get(set_id, 0) + 1
        return members

    @staticmethod
    def exclude_panoplie_items(
        equipments: List[Equipment],
        min_set_size: int = 5,
    ) -> tuple:
        """Split the pool into (retained, excluded) by panoplie size.

        Items in a set with at least ``min_set_size`` members present in the
        pool are excluded; everything else — including all setless items — is
        retained. ``min_set_size`` of 99 or higher disables the filter.

        Returns ``(retained, excluded)`` as two lists, mirroring
        ``filter_by_density_ratio`` so callers can treat them alike.
        """
        if min_set_size >= 99:
            return list(equipments), []

        set_sizes = SetExclusionFilter.summarize_set_sizes(equipments)
        retained: List[Equipment] = []
        excluded: List[Equipment] = []
        for equipment in equipments:
            set_id = getattr(equipment, "set_id", None)
            if set_id is not None and set_sizes.get(int(set_id), 0) >= min_set_size:
                excluded.append(equipment)
            else:
                retained.append(equipment)

        if excluded:
            logger.info(
                f"Set exclusion (min set size {min_set_size}): dropped "
                f"{len(excluded)} / {len(equipments)} equipment"
            )
        return retained, excluded

    @staticmethod
    def summarize_excluded(equipments: List[Equipment]) -> dict[str, int]:
        """Report the shape of an exclusion so it cannot read as a coverage bug.

        Per metric N10, a deliberate scope decision must be visible in the run
        manifest: band and slot breakdowns of the removed items.
        """
        by_band: dict[str, int] = defaultdict(int)
        by_slot: dict[str, int] = defaultdict(int)
        for equipment in equipments:
            level = equipment.level if equipment.level is not None else 0
            band = int(level) // 20
            by_band[f"band_{band}"] += 1
            type_name = equipment.type.get("name", "unknown") if equipment.type else "unknown"
            by_slot[type_name] += 1
        return {"total": len(equipments), "by_band": dict(by_band), "by_slot": dict(by_slot)}


