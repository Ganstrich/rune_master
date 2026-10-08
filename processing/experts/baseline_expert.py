"""Simple objective-driven baseline grouping expert."""

from typing import Any, Dict, List, Optional, Set

from models import Equipment
from processing.config_dataclass import ProcessingConfig
from processing.experts.base import GroupingExpert
from processing.group_metrics import GroupMetrics
from processing.policy import GroupAcceptancePolicy
from processing.valuation.focus import break_density
from processing.valuation.objective import GroupCandidate, GroupObjective


class BaselineExpert(GroupingExpert):
    """Pack high-density items greedily using the injected objective."""

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
        ordered = sorted(
            equipments,
            key=lambda equipment: (break_density(equipment), equipment.ankama_id),
            reverse=True,
        )[: max(config.group_max_size, config.group_min_size)]
        if not ordered:
            return []

        group = [ordered.pop(0)]
        while ordered and len(group) < config.group_max_size:
            candidate = GroupCandidate(group, config.excluded_resource_ids)
            next_item = max(
                ordered,
                key=lambda item: self.objective.marginal(candidate, item)
                if self.objective
                else break_density(item),
            )
            group.append(next_item)
            ordered.remove(next_item)

        group_data = GroupMetrics.build_group_dict(
            group,
            cache_manager=self.cache_manager,
            excluded_resource_ids=config.excluded_resource_ids,
            quality_weights=config.group_quality_weights,
        )
        if not policy.accepts(group_data):
            return []
        group_data["selection_method"] = "baseline"
        group_data["expert_name"] = self.name
        return [group_data]