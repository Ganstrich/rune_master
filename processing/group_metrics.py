"""Shared calculations for equipment group metrics."""

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Set

from models import Equipment
from processing.blocks.recipes import iter_recipe
from processing.quality_metrics import GroupQualityEvaluator, GroupQualityWeights
from processing.valuation.focus import break_density


class GroupMetrics:
    """Single source of truth for group-level resource and density metrics."""

    @staticmethod
    def shared_resources(
        equipments: List[Equipment],
        excluded_resource_ids: Set[int] | None = None,
    ) -> set[int]:
        """Return resource IDs used by at least two equipments."""
        excluded = excluded_resource_ids or set()
        usage: Dict[int, int] = defaultdict(int)
        for equipment in equipments:
            resource_ids = {
                resource_id
                for resource_id, _quantity in iter_recipe(equipment)
            }
            for resource_id in resource_ids:
                usage[resource_id] += 1
        return {
            resource_id
            for resource_id, count in usage.items()
            if count >= 2 and resource_id not in excluded
        }

    @staticmethod
    def shared_resources_count(
        equipments: List[Equipment],
        excluded_resource_ids: Set[int] | None = None,
    ) -> int:
        """Return the number of shared resource IDs."""
        return len(GroupMetrics.shared_resources(equipments, excluded_resource_ids))

    @staticmethod
    def total_unique_resources(equipments: List[Equipment]) -> set[int]:
        """Return all resource IDs used by the equipment."""
        return {
            resource_id
            for equipment in equipments
            for resource_id, _quantity in iter_recipe(equipment)
        }

    @staticmethod
    def sharing_efficiency(
        equipments: List[Equipment],
        excluded_resource_ids: Set[int] | None = None,
    ) -> float:
        """Return shared resource count divided by total unique resources."""
        total_unique = len(GroupMetrics.total_unique_resources(equipments))
        if total_unique == 0:
            return 0.0
        return GroupMetrics.shared_resources_count(equipments, excluded_resource_ids) / total_unique

    @staticmethod
    def aggregate_resources(
        equipments: List[Equipment],
        cache_manager: Any = None,
    ) -> Dict[int, dict]:
        """Aggregate recipe quantities and resource metadata for a group."""
        ingredients = defaultdict(
            lambda: {
                "name": None,
                "total_quantity": 0,
                "used_in_equipments": [],
                "quantity_per_equipment": {},
                "quantity_per_equipment_by_id": {},
                "image_url": None,
            }
        )

        for equipment in equipments:
            for resource_id, quantity in iter_recipe(equipment):
                ingredient = ingredients[resource_id]
                ingredient["total_quantity"] += quantity
                equipment_name = getattr(equipment, "name", None) or str(
                    getattr(equipment, "ankama_id", "?")
                )
                ingredient["used_in_equipments"].append(equipment_name)
                ingredient["quantity_per_equipment"][equipment_name] = quantity
                ingredient["quantity_per_equipment_by_id"][int(equipment.ankama_id)] = quantity

                if ingredient["name"] is None and cache_manager:
                    try:
                        resource_data = cache_manager.get_resource(resource_id)
                        if resource_data:
                            ingredient["name"] = resource_data.get("name")
                            image_urls = resource_data.get("image_urls", {})
                            ingredient["image_url"] = image_urls.get("icon") or image_urls.get("sd")
                    except Exception:
                        pass

                if ingredient["name"] is None:
                    ingredient["name"] = f"Resource {resource_id}"

        return dict(ingredients)

    @staticmethod
    def average_density(equipments: List[Equipment]) -> float:
        """Return the average stat_weight/level density across the equipment."""
        densities = [
            equipment.stat_weight / equipment.level
            for equipment in equipments
            if getattr(equipment, "level", 0)
            and getattr(equipment, "stat_weight", None) is not None
        ]
        if not densities:
            return 0.0
        return sum(densities) / len(densities)

    @staticmethod
    def build_group_dict(
        equipments: List[Equipment],
        cache_manager: Any = None,
        excluded_resource_ids: Set[int] | None = None,
        quality_weights: GroupQualityWeights | None = None,
    ) -> Dict[str, Any]:
        """Build the canonical group metadata dictionary."""
        if not equipments:
            return {}

        total_ingredients = GroupMetrics.aggregate_resources(equipments, cache_manager)
        quality_metrics = GroupQualityEvaluator(quality_weights).evaluate(
            equipments, excluded_resource_ids
        )
        return {
            "equipments": equipments,
            "shared_resources_count": GroupMetrics.shared_resources_count(
                equipments, excluded_resource_ids
            ),
            "total_shared_resources": GroupMetrics.shared_resources(
                equipments, excluded_resource_ids
            ),
            "sharing_efficiency": GroupMetrics.sharing_efficiency(
                equipments, excluded_resource_ids
            ),
            "average_density": GroupMetrics.average_density(equipments),
            "break_density": {
                int(equipment.ankama_id): break_density(equipment)
                for equipment in equipments
            },
            "items_per_line_item": (
                len(equipments) / len(total_ingredients) if total_ingredients else 0.0
            ),
            "total_ingredients": total_ingredients,
            "unique_ingredients_count": len(total_ingredients),
            "total_items_needed": sum(
                ingredient["total_quantity"] for ingredient in total_ingredients.values()
            ),
            "group_size": len(equipments),
            "largest_set_share": quality_metrics.largest_set_share,
            "quality_metrics": quality_metrics.to_dict(),
            "quality_score": quality_metrics.quality_score,
        }
