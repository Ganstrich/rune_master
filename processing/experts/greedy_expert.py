"""Greedy objective-driven grouping expert.

The graph experts can only propose communities of the resource-similarity
graph, so items below the shared-resource threshold are never grouped at all.
This expert grows groups directly against the objective instead, which reaches
items the graph discards.
"""

from typing import Any, Dict, List, Optional, Set

from models import Equipment
from processing.blocks.recipes import recipe_resource_ids
from processing.config_dataclass import ProcessingConfig
from processing.experts.base import GroupingExpert
from processing.group_metrics import GroupMetrics
from processing.policy import GroupAcceptancePolicy
from processing.valuation.objective import GroupCandidate, GroupObjective
from processing.valuation.overlap import OverlapObjective
from processing.valuation.focus import break_density


class GreedyGroupingExpert(GroupingExpert):
    """Grow each group by repeatedly adding the item the objective likes most."""

    def __init__(
        self,
        cache_manager: Optional[Any] = None,
        api_client: Optional[Any] = None,
        objective: Optional[GroupObjective] = None,
        policy: Optional[GroupAcceptancePolicy] = None,
    ):
        super().__init__("GreedyExpert", cache_manager, api_client, objective, policy)

    def discover_groups(
        self,
        equipments: List[Equipment],
        config: ProcessingConfig,
        precomputed_graph: Optional[Any] = None,
        precomputed_resources: Optional[Dict[int, Set[int]]] = None,
    ) -> List[Dict[str, Any]]:
        """Seed from uncovered items and grow each group against the objective."""
        print(f"      [{self.name}] Growing groups against the objective...")
        objective = self.objective or OverlapObjective(config.group_quality_weights)
        policy = self.policy or GroupAcceptancePolicy(config)
        excluded = set(config.excluded_resource_ids or set())

        by_id = {e.ankama_id: e for e in equipments}
        resources = {
            e.ankama_id: recipe_resource_ids(e) - excluded for e in equipments
        }
        neighbours: Dict[int, Set[int]] = {}
        for equipment_id, resource_ids in resources.items():
            for resource_id in resource_ids:
                neighbours.setdefault(resource_id, set()).add(equipment_id)

        seeds = sorted(equipments, key=break_density, reverse=True)
        if config.greedy_seed_limit:
            seeds = seeds[: config.greedy_seed_limit]

        groups: List[Dict[str, Any]] = []
        seen: Set[frozenset] = set()
        covered: Set[int] = set()

        for seed in seeds:
            if seed.ankama_id in covered or not resources[seed.ankama_id]:
                continue
            members = self._grow(
                seed, by_id, resources, neighbours, objective, config, excluded, covered
            )
            if len(members) < config.group_min_size:
                continue
            fingerprint = frozenset(e.ankama_id for e in members)
            if fingerprint in seen:
                continue
            group = GroupMetrics.build_group_dict(
                members,
                cache_manager=self.cache_manager,
                excluded_resource_ids=excluded,
                quality_weights=config.group_quality_weights,
            )
            if not policy.accepts(group):
                continue
            seen.add(fingerprint)
            covered |= fingerprint
            group["expert_name"] = self.name
            group["selection_method"] = "greedy"
            groups.append(group)

        print(f"      [{self.name}] Built {len(groups)} groups covering {len(covered)} items")
        return groups

    @staticmethod
    def _grow(
        seed: Equipment,
        by_id: Dict[int, Equipment],
        resources: Dict[int, Set[int]],
        neighbours: Dict[int, Set[int]],
        objective: GroupObjective,
        config: ProcessingConfig,
        excluded: Set[int],
        covered: Set[int],
    ) -> List[Equipment]:
        """Add the best-scoring admissible item until nothing improves the group.

        Groups are kept disjoint: the portfolio evaluator penalises duplicate
        assignments, so an overlapping proposal scores worse than a small clean one.
        """
        members = [seed]
        member_ids = {seed.ankama_id}
        pooled = set(resources[seed.ankama_id])
        set_counts: Dict[int, int] = {}
        if seed.set_id is not None:
            set_counts[seed.set_id] = 1

        candidate_cap = max(config.greedy_candidate_limit, 1)
        current = GroupCandidate(members, excluded)
        current_score = objective.score(current)

        while len(members) < config.group_max_size:
            pool = {
                equipment_id
                for resource_id in pooled
                for equipment_id in neighbours.get(resource_id, ())
                if equipment_id not in member_ids and equipment_id not in covered
            }
            if not pool:
                break
            # Shared-resource count is a cheap proxy used only to shortlist.
            ranked = sorted(
                pool,
                key=lambda eid: len(resources[eid] & pooled),
                reverse=True,
            )[:candidate_cap]

            best_item: Optional[Equipment] = None
            best_score = current_score
            for equipment_id in ranked:
                item = by_id[equipment_id]
                if GreedyGroupingExpert._breaks_set_cap(item, set_counts, len(members), config):
                    continue
                score = objective.score(current.with_item(item))
                if score > best_score:
                    best_score = score
                    best_item = item

            if best_item is None:
                break
            members.append(best_item)
            member_ids.add(best_item.ankama_id)
            pooled |= resources[best_item.ankama_id]
            if best_item.set_id is not None:
                set_counts[best_item.set_id] = set_counts.get(best_item.set_id, 0) + 1
            current = GroupCandidate(members, excluded)
            current_score = best_score

        return members

    @staticmethod
    def _breaks_set_cap(
        item: Equipment,
        set_counts: Dict[int, int],
        group_size: int,
        config: ProcessingConfig,
    ) -> bool:
        """Reject an item that would push one panoplie past the configured share."""
        if item.set_id is None:
            return False
        projected = set_counts.get(item.set_id, 0) + 1
        return projected / (group_size + 1) > config.group_max_set_share
