"""Portfolio-level mutation and crossover operators for evolutionary search."""
import random
from typing import Any, Dict, List, Optional

from processing.config_dataclass import ProcessingConfig
from processing.evolutionary_search_state import PortfolioCandidate
from processing.policy import GroupAcceptancePolicy


class EvolutionaryOperators:
    """Portfolio-level mutation and crossover operators.

    Each operator returns a valid portfolio that passes the acceptance policy,
    or a marked-infeasible candidate if no valid portfolio could be created.
    """

    def __init__(
        self,
        equipments: List[Any],
        eq_by_id: Dict[int, Any],
        equipment_graph: Any,
        policy: GroupAcceptancePolicy,
        config: ProcessingConfig,
        rng: random.Random,
    ):
        self.equipments = equipments
        self.eq_by_id = eq_by_id
        self.graph = equipment_graph
        self.policy = policy
        self.config = config
        self.rng = rng

    def add_equipment_to_group(
        self, portfolio: PortfolioCandidate, config: ProcessingConfig
    ) -> PortfolioCandidate:
        """Add a graph-adjacent equipment to a random group."""
        if not portfolio.groups or self.rng.random() > 0.5:
            return portfolio

        group_idx = self.rng.randint(0, len(portfolio.groups) - 1)
        group = portfolio.groups[group_idx]
        current_size = len(group.get("equipments", []))

        if current_size >= config.group_max_size:
            return portfolio

        assigned_ids = set(portfolio.equipment_ids())
        current_group_ids = {eq.ankama_id for eq in group.get("equipments", [])}

        candidates = set()
        for eq in group.get("equipments", []):
            for neighbor in self.graph.neighbors(eq.ankama_id):
                if neighbor not in assigned_ids and neighbor in self.eq_by_id:
                    candidates.add(neighbor)

        if not candidates:
            return portfolio

        chosen_id = self.rng.choice(list(candidates))
        new_eq = self.eq_by_id[chosen_id]

        new_groups = list(portfolio.groups)
        new_group = dict(group)
        new_group["equipments"] = group.get("equipments", []) + [new_eq]
        new_groups[group_idx] = new_group

        return PortfolioCandidate(
            groups=tuple(new_groups),
            provenance=portfolio.provenance,
            generation=portfolio.generation + 1,
            parent_ids=frozenset([portfolio.fingerprint] + list(portfolio.parent_ids)),
            metadata={**portfolio.metadata, "operator": "add_equipment"},
        )

    def remove_weakest_equipment(
        self, portfolio: PortfolioCandidate, config: ProcessingConfig
    ) -> PortfolioCandidate:
        """Remove weakest marginal equipment from a random group."""
        if not portfolio.groups or self.rng.random() > 0.5:
            return portfolio

        group_idx = self.rng.randint(0, len(portfolio.groups) - 1)
        group = portfolio.groups[group_idx]
        equipments = group.get("equipments", [])

        if len(equipments) <= config.group_min_size:
            return portfolio

        if not equipments:
            return portfolio

        weakest = self.rng.choice(equipments)

        new_groups = list(portfolio.groups)
        new_group = dict(group)
        new_group["equipments"] = [
            eq for eq in equipments if eq.ankama_id != weakest.ankama_id
        ]
        new_groups[group_idx] = new_group

        return PortfolioCandidate(
            groups=tuple(new_groups),
            provenance=portfolio.provenance,
            generation=portfolio.generation + 1,
            parent_ids=frozenset([portfolio.fingerprint] + list(portfolio.parent_ids)),
            metadata={**portfolio.metadata, "operator": "remove_equipment"},
        )

    def swap_equipment_for_neighbor(
        self, portfolio: PortfolioCandidate
    ) -> PortfolioCandidate:
        """Swap equipment in a group for a graph neighbor."""
        if not portfolio.groups or self.rng.random() > 0.5:
            return portfolio

        group_idx = self.rng.randint(0, len(portfolio.groups) - 1)
        group = portfolio.groups[group_idx]
        equipments = group.get("equipments", [])

        if not equipments:
            return portfolio

        assigned_ids = set(portfolio.equipment_ids())
        eq_to_swap = self.rng.choice(equipments)

        candidates = {
            neighbor
            for neighbor in self.graph.neighbors(eq_to_swap.ankama_id)
            if neighbor not in assigned_ids and neighbor in self.eq_by_id
        }

        if not candidates:
            return portfolio

        new_eq_id = self.rng.choice(list(candidates))
        new_eq = self.eq_by_id[new_eq_id]

        new_groups = list(portfolio.groups)
        new_group = dict(group)
        new_group["equipments"] = [
            new_eq if eq.ankama_id == eq_to_swap.ankama_id else eq
            for eq in equipments
        ]
        new_groups[group_idx] = new_group

        return PortfolioCandidate(
            groups=tuple(new_groups),
            provenance=portfolio.provenance,
            generation=portfolio.generation + 1,
            parent_ids=frozenset([portfolio.fingerprint] + list(portfolio.parent_ids)),
            metadata={**portfolio.metadata, "operator": "swap_equipment"},
        )

    def split_oversized_group(
        self, portfolio: PortfolioCandidate, config: ProcessingConfig
    ) -> PortfolioCandidate:
        """Split an oversized group into two smaller groups."""
        oversized = [
            (i, g)
            for i, g in enumerate(portfolio.groups)
            if len(g.get("equipments", [])) > config.group_max_size * 0.8
        ]

        if not oversized or self.rng.random() > 0.5:
            return portfolio

        group_idx, group = self.rng.choice(oversized)
        equipments = list(group.get("equipments", []))

        if len(equipments) < config.group_min_size * 2:
            return portfolio

        split_point = self.rng.randint(
            config.group_min_size, len(equipments) - config.group_min_size
        )
        group1_eqs = equipments[:split_point]
        group2_eqs = equipments[split_point:]

        new_groups = list(portfolio.groups)
        new_group1 = {**group, "equipments": group1_eqs}
        new_group2 = {**group, "equipments": group2_eqs}
        new_groups[group_idx] = new_group1
        new_groups.append(new_group2)

        return PortfolioCandidate(
            groups=tuple(new_groups),
            provenance=portfolio.provenance,
            generation=portfolio.generation + 1,
            parent_ids=frozenset([portfolio.fingerprint] + list(portfolio.parent_ids)),
            metadata={**portfolio.metadata, "operator": "split_group"},
        )

    def merge_compatible_groups(
        self, portfolio: PortfolioCandidate, config: ProcessingConfig
    ) -> PortfolioCandidate:
        """Merge two compatible small groups if result is valid."""
        groups = portfolio.groups

        if len(groups) < 2 or self.rng.random() > 0.5:
            return portfolio

        small_groups = [
            (i, g)
            for i, g in enumerate(groups)
            if len(g.get("equipments", [])) < config.group_min_size * 2
        ]

        if len(small_groups) < 2:
            return portfolio

        idx1, group1 = self.rng.choice(small_groups)
        idx2, group2 = self.rng.choice(small_groups)

        if idx1 == idx2:
            return portfolio

        merged_eqs = list(group1.get("equipments", [])) + list(
            group2.get("equipments", [])
        )

        if len(merged_eqs) > config.group_max_size:
            return portfolio

        new_groups = [
            g for i, g in enumerate(groups) if i not in (idx1, idx2)
        ]
        merged_group = {**group1, "equipments": merged_eqs}
        new_groups.append(merged_group)

        return PortfolioCandidate(
            groups=tuple(new_groups),
            provenance=portfolio.provenance,
            generation=portfolio.generation + 1,
            parent_ids=frozenset([portfolio.fingerprint] + list(portfolio.parent_ids)),
            metadata={**portfolio.metadata, "operator": "merge_groups"},
        )

    def move_equipment_between_groups(
        self, portfolio: PortfolioCandidate, config: ProcessingConfig
    ) -> PortfolioCandidate:
        """Move an equipment from one group to another."""
        if len(portfolio.groups) < 2 or self.rng.random() > 0.5:
            return portfolio

        source_idx = self.rng.randint(0, len(portfolio.groups) - 1)
        source_group = portfolio.groups[source_idx]
        source_eqs = source_group.get("equipments", [])

        if len(source_eqs) <= config.group_min_size:
            return portfolio

        eq_to_move = self.rng.choice(source_eqs)

        target_idx = self.rng.randint(0, len(portfolio.groups) - 1)
        if target_idx == source_idx:
            target_idx = (target_idx + 1) % len(portfolio.groups)

        target_group = portfolio.groups[target_idx]
        target_eqs = target_group.get("equipments", [])

        if len(target_eqs) >= config.group_max_size:
            return portfolio

        new_groups = list(portfolio.groups)
        new_source = {**source_group, "equipments": [
            eq for eq in source_eqs if eq.ankama_id != eq_to_move.ankama_id
        ]}
        new_target = {**target_group, "equipments": target_eqs + [eq_to_move]}
        new_groups[source_idx] = new_source
        new_groups[target_idx] = new_target

        return PortfolioCandidate(
            groups=tuple(new_groups),
            provenance=portfolio.provenance,
            generation=portfolio.generation + 1,
            parent_ids=frozenset([portfolio.fingerprint] + list(portfolio.parent_ids)),
            metadata={**portfolio.metadata, "operator": "move_equipment"},
        )

    def cold_start_portfolio(self) -> PortfolioCandidate:
        """Generate a random portfolio from scratch."""
        available = set(self.graph.nodes()) & set(self.eq_by_id.keys())
        groups = []

        target_group_count = self.rng.randint(3, 8)

        while available and len(groups) < target_group_count:
            seed_id = self.rng.choice(tuple(available))
            target_size = self.rng.randint(
                self.config.group_min_size, self.config.group_max_size
            )
            group_ids = {seed_id}

            while len(group_ids) < target_size and available:
                candidates = {
                    neighbor
                    for gid in group_ids
                    for neighbor in self.graph.neighbors(gid)
                    if neighbor in available and neighbor not in group_ids
                }
                if not candidates:
                    break
                group_ids.add(self.rng.choice(list(candidates)))

            available -= group_ids
            if len(group_ids) >= self.config.group_min_size:
                eq_list = [self.eq_by_id[gid] for gid in group_ids]
                groups.append({"equipments": eq_list})

        if not groups:
            return PortfolioCandidate(
                groups=(),
                provenance="cold_start",
                feasibility_status="rejected",
                rejection_reason="Failed to generate cold-start portfolio",
            )

        return PortfolioCandidate(
            groups=tuple(groups),
            provenance="cold_start",
            fingerprint=PortfolioCandidate.compute_fingerprint(groups),
        )
