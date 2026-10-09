"""Simple objective-driven baseline grouping expert."""
from typing import Any, Dict, List, Optional, Set

from models import Equipment
from processing.blocks.recipes import recipe_resource_ids
from processing.config_dataclass import ProcessingConfig
from processing.experts.base import GroupingExpert
from processing.group_metrics import GroupMetrics
from processing.policy import GroupAcceptancePolicy
from processing.valuation.focus import break_density
from processing.valuation.objective import GroupCandidate, GroupObjective


class BaselineExpert(GroupingExpert):
    """Pack high-density items greedily using the injected objective.

    Grows one group at a time, respecting the line-item budget during
    growth rather than only checking it at the end.
    """

    def __init__(
        self,
        cache_manager: Optional[Any] = None,
        api_client: Optional[Any] = None,
        objective: Optional[GroupObjective] = None,
        policy: Optional[GroupAcceptancePolicy] = None,
    ) -> None:
        super().__init__("BaselineExpert", cache_manager, api_client, objective, policy)

    def discover_groups(
        self,
        equipments: List[Equipment],
        config: ProcessingConfig,
        precomputed_graph: Optional[Any] = None,
        precomputed_resources: Optional[Dict[int, Set[int]]] = None,
    ) -> List[Dict[str, Any]]:
        del precomputed_graph, precomputed_resources
        policy = self.policy or GroupAcceptancePolicy(config)
        excluded = set(config.excluded_resource_ids or set())
        max_line_items = config.max_line_items
        max_total_units = config.max_total_units

        ordered = sorted(
            equipments,
            key=lambda equipment: (break_density(equipment), equipment.ankama_id),
            reverse=True,
        )
        if not ordered:
            return []

        groups: List[Dict[str, Any]] = []
        covered: Set[int] = set()

        for seed in ordered:
            if seed.ankama_id in covered:
                continue
            members = [seed]
            member_ids = {seed.ankama_id}
            pooled = recipe_resource_ids(seed) - excluded
            total_units = sum(
                req.quantity for req in seed.recipe if req.resource_id not in excluded
            )

            candidates = [
                eq for eq in ordered
                if eq.ankama_id not in covered and eq.ankama_id != seed.ankama_id
            ]

            while candidates and len(members) < config.group_max_size:
                candidate = GroupCandidate(members, excluded)
                best_item = None
                best_score = None
                for item in candidates:
                    item_resources = recipe_resource_ids(item) - excluded
                    new_line_items = len(pooled | item_resources)
                    if new_line_items > max_line_items:
                        continue
                    item_units = sum(
                        req.quantity for req in item.recipe if req.resource_id not in excluded
                    )
                    if total_units + item_units > max_total_units:
                        continue
                    score = (
                        self.objective.marginal(candidate, item)
                        if self.objective
                        else break_density(item)
                    )
                    if best_score is None or score > best_score:
                        best_score = score
                        best_item = item

                if best_item is None:
                    break

                members.append(best_item)
                member_ids.add(best_item.ankama_id)
                pooled |= recipe_resource_ids(best_item) - excluded
                total_units += sum(
                    req.quantity for req in best_item.recipe if req.resource_id not in excluded
                )
                candidates = [
                    eq for eq in candidates if eq.ankama_id != best_item.ankama_id
                ]

            if len(members) < config.group_min_size:
                continue

            group_data = GroupMetrics.build_group_dict(
                members,
                cache_manager=self.cache_manager,
                excluded_resource_ids=excluded,
                quality_weights=config.group_quality_weights,
            )
            if not policy.accepts(group_data):
                continue

            covered |= member_ids
            group_data["selection_method"] = "baseline"
            group_data["expert_name"] = self.name
            groups.append(group_data)

        return groups
