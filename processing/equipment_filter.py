"""Equipment filtering by density/level ratio.

Provides filtering strategies to reduce equipment pool based on stat density
(stat_weight per level). Used for both random grouping and exploration.
"""

import logging
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
    def filter_by_density_ratio(equipments: List[Equipment], ratio: float) -> tuple:
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

    @staticmethod
    def get_pool_stats(equipments: List[Equipment]) -> dict:
        """Get statistics about equipment pool.

        Args:
            equipments: List of Equipment objects

        Returns:
            Dict with pool statistics
        """
        with_weight = [e for e in equipments if e.stat_weight is not None]
        without_weight = [e for e in equipments if e.stat_weight is None]

        if not with_weight:
            return {
                "total": len(equipments),
                "with_stat_weight": 0,
                "without_stat_weight": len(without_weight),
                "avg_density": None,
                "min_density": None,
                "max_density": None,
            }

        densities = [
            e.stat_weight / e.level
            for e in with_weight
            if e.level > 0 and e.stat_weight is not None
        ]

        return {
            "total": len(equipments),
            "with_stat_weight": len(with_weight),
            "without_stat_weight": len(without_weight),
            "avg_density": sum(densities) / len(densities) if densities else None,
            "min_density": min(densities) if densities else None,
            "max_density": max(densities) if densities else None,
        }
