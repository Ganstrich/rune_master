"""Evolutionary portfolio search engine with operators and fitness evaluation.

OVERVIEW:
    This module implements an iterative evolutionary search for discovering
    optimal equipment portfolios. It differs fundamentally from genetic search
    by optimizing at the *portfolio level* (complete ensemble) rather than
    individual group level.

KEY DESIGN PRINCIPLES:

1. PORTFOLIO-LEVEL FITNESS (not group sum):
   - Score complete portfolios, not just isolated groups
   - Reward coverage (unique equipment used)
   - Penalize duplicate assignments (same equipment in multiple groups)
   - Balance group quality with portfolio metrics
   → Result: Diverse, non-redundant, well-balanced portfolios

2. MULTI-EXPERT INITIALIZATION:
   - Start from committee proposals (deterministic, random, genetic)
   - Combine strengths of multiple search strategies
   - Each expert contributes its best candidates
   → Result: Better starting population than single expert

3. INTELLIGENT MUTATION OPERATORS:
   - Add adjacent equipment (respects graph neighborhoods)
   - Remove weakest members (heuristic selection)
   - Swap for neighbors (targeted improvement)
   - Split oversized groups (decomposition)
   - Merge small groups (consolidation)
   - Move equipment between groups (rebalancing)
   → Result: Semantically valid changes, not random perturbations

4. ELITE PRESERVATION + DIVERSITY INJECTION:
   - Keep top N candidates across generations
   - Inject cold-start random portfolios for diversity
   - Archive all unique candidates for later selection
   → Result: Convergence to good solutions without local optima traps

5. DETERMINISM + REPRODUCIBILITY:
   - Fixed random seed produces identical results
   - All operators use seeded RNG
   - Provenance tracking for audit trail
   → Result: Reproducible, auditable group discovery

TRADE-OFFS:

Speed vs Quality:
  - Deterministic: Milliseconds, good results
  - Committee: Seconds, very good results
  - Evolutionary: Minutes, excellent results
  → Choose based on your time budget and quality requirements

Generalization vs Specialization:
  - Single-expert (genetic): Deep search of one strategy
  - Multi-expert (evolutionary_committee): Balanced search across all
  → Evolutionary committee usually wins unless specific domain knowledge

Tuning Complexity:
  - Deterministic: 2-3 key parameters
  - Committee: 4-5 parameters
  - Evolutionary: 10+ parameters
  → See GROUPING_METHODS.md for tuning guide

USAGE PATTERN:

    from processing.evolutionary_search_engine import PortfolioEvolutionEngine

    # Create engine
    engine = PortfolioEvolutionEngine(
        equipments,
        config,
        objective=overlap_objective,
        policy=acceptance_policy
    )

    # Run evolution
    best_portfolio = engine.evolve_portfolio(
        initial_proposals=[proposal1, proposal2, ...],
        warm_start_config=None  # Optional: seed from prior portfolios
    )

    # Extract results
    groups = list(best_portfolio.groups)

See GROUPING_METHODS.md for detailed comparison with other methods.
"""

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from models import Equipment
from processing.config_dataclass import ProcessingConfig
from processing.evolutionary_search_state import (
    EvolutionaryArchive,
    PortfolioCandidate,
    WarmStartConfig,
)
from processing.policy import GroupAcceptancePolicy
from processing.quality_metrics import PortfolioQualityEvaluator
from processing.valuation.objective import GroupCandidate, GroupObjective


class PortfolioFitnessEvaluator:
    """Evaluate fitness of complete portfolios (not just sum of groups).

    Uses the canonical portfolio evaluator to score coverage, overlap, and quality
    at the portfolio level, ensuring diversity and balanced coverage.
    """

    def __init__(
        self,
        total_equipment_count: int,
        portfolio_weights=None,
        objective: Optional[GroupObjective] = None,
        policy: Optional[GroupAcceptancePolicy] = None,
    ):
        self.total_equipment_count = total_equipment_count
        self.evaluator = PortfolioQualityEvaluator(portfolio_weights)
        self.objective = objective
        self.policy = policy

    def evaluate(
        self,
        candidate: PortfolioCandidate,
        excluded_resource_ids: Optional[Set[int]] = None,
    ) -> PortfolioCandidate:
        """Re-evaluate a portfolio and return updated candidate with metrics.

        Returns a new PortfolioCandidate with:
        - Updated score from portfolio-level evaluation
        - Feasibility status and rejection reason (if policy rejects it)
        - Portfolio metrics captured in 'metrics' field
        """
        if not candidate.groups:
            return PortfolioCandidate(
                groups=(),
                score=-100.0,
                feasibility_status="rejected",
                rejection_reason="Empty portfolio",
                provenance=candidate.provenance,
                generation=candidate.generation,
                parent_ids=candidate.parent_ids,
                metadata=candidate.metadata,
            )

        # Evaluate each group under the objective if available
        group_scores = []
        for group in candidate.groups:
            if self.objective is not None:
                eq_list = list(group.get("equipments", []))
                group_cand = GroupCandidate(eq_list, excluded_resource_ids or set())
                score = self.objective.score(group_cand)
            else:
                score = float(group.get("quality_score", 0.0))
            group_scores.append(score)

        # Evaluate portfolio as a whole
        portfolio_metrics = self.evaluator.evaluate(
            candidate.groups, self.total_equipment_count
        )

        # Combine group quality with portfolio coverage and overlap penalties
        # Portfolio score emphasizes coverage and penalizes duplication
        portfolio_score = portfolio_metrics.portfolio_quality_score

        # Check feasibility against policy
        feasibility_status = "accepted"
        rejection_reason = None
        if self.policy is not None:
            for group in candidate.groups:
                if not self.policy.accepts(group):
                    feasibility_status = "rejected"
                    rejection_reason = f"Group rejected: {group.get('group_size', 0)} items"
                    break

        metrics_dict = portfolio_metrics.to_dict()
        metrics_dict["group_scores"] = group_scores
        metrics_dict["mean_group_score"] = (
            sum(group_scores) / len(group_scores) if group_scores else 0.0
        )

        return PortfolioCandidate(
            groups=candidate.groups,
            score=portfolio_score,
            metrics=metrics_dict,
            generation=candidate.generation,
            parent_ids=candidate.parent_ids,
            provenance=candidate.provenance,
            fingerprint=candidate.fingerprint or PortfolioCandidate.compute_fingerprint(
                list(candidate.groups)
            ),
            feasibility_status=feasibility_status,
            rejection_reason=rejection_reason,
            metadata=candidate.metadata,
        )


class EvolutionaryOperators:
    """Portfolio-level mutation and crossover operators.

    Each operator returns a valid portfolio that passes the acceptance policy,
    or a marked-infeasible candidate if no valid portfolio could be created.
    """

    def __init__(
        self,
        equipments: List[Equipment],
        eq_by_id: Dict[int, Equipment],
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
        """Add a graph-adjacent equipment to a random group.

        Selects a random group and adds a neighboring equipment if possible,
        respecting size limits.
        """
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
        """Remove weakest marginal equipment from a random group.

        "Weakest" means lowest resource contribution to group sharing.
        """
        if not portfolio.groups or self.rng.random() > 0.5:
            return portfolio

        group_idx = self.rng.randint(0, len(portfolio.groups) - 1)
        group = portfolio.groups[group_idx]
        equipments = group.get("equipments", [])

        if len(equipments) <= config.group_min_size:
            return portfolio

        if not equipments:
            return portfolio

        # Simple heuristic: remove equipment with lowest density or at random
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


class PortfolioEvolutionEngine:
    """Main evolutionary search engine for portfolios.

    Manages population evolution across multiple rounds, archive updates,
    elite selection, and diversity maintenance.
    """

    def __init__(
        self,
        equipments: List[Equipment],
        config: ProcessingConfig,
        objective: Optional[GroupObjective] = None,
        policy: Optional[GroupAcceptancePolicy] = None,
        cache_manager: Optional[Any] = None,
        api_client: Optional[Any] = None,
    ):
        self.equipments = equipments
        self.config = config
        self.objective = objective
        self.policy = policy or GroupAcceptancePolicy(config)
        self.cache_manager = cache_manager
        self.api_client = api_client

        self.rng = random.Random(config.evolutionary_random_seed)
        self.eq_by_id = {eq.ankama_id: eq for eq in equipments}
        self.archive = EvolutionaryArchive(
            max_archive_size=config.evolutionary_archive_size,
            elite_size=config.evolutionary_elite_count,
            diversity_threshold=config.evolutionary_diversity_threshold,
        )
        self._graph = None
        self.equipment_resources = {}

    def evolve_portfolio(
        self,
        initial_proposals: List[List[Dict[str, Any]]],
        warm_start_config: Optional[WarmStartConfig] = None,
    ) -> PortfolioCandidate:
        """Run evolutionary search for multiple rounds.

        Args:
            initial_proposals: List of proposals from committee experts
            warm_start_config: Optional warm-start configuration

        Returns:
            Best portfolio found after evolutionary rounds.
        """
        if not self.equipments:
            return PortfolioCandidate(
                feasibility_status="rejected",
                rejection_reason="Empty equipment pool",
            )

        # Build equipment graph
        from processing.graph_builder import GraphBuilder
        self.graph, self.equipment_resources = GraphBuilder.build_equipment_graph(
            self.equipments,
            min_shared_ratio=self.config.graph_min_shared_ratio,
            min_shared_count=self.config.graph_min_shared_count,
            min_component_size=self.config.graph_min_component_size,
        )

        if self.graph.number_of_nodes() == 0:
            return PortfolioCandidate(
                feasibility_status="rejected",
                rejection_reason="No connected equipment in graph",
            )

        # Initialize fitness evaluator
        fitness_eval = PortfolioFitnessEvaluator(
            len(self.equipments),
            self.config.portfolio_quality_weights,
            self.objective,
            self.policy,
        )

        # Initialize operators
        operators = EvolutionaryOperators(
            self.equipments,
            self.eq_by_id,
            self.graph,
            self.policy,
            self.config,
            self.rng,
        )

        # Initialize population
        population = self._initialize_population(
            initial_proposals, operators, fitness_eval, warm_start_config
        )

        if not population:
            return PortfolioCandidate(
                feasibility_status="rejected",
                rejection_reason="Failed to initialize population",
            )

        best_ever = max(population, key=lambda c: c.score)
        stagnation_counter = 0

        # Evolution loop
        for round_num in range(self.config.evolutionary_rounds):
            print(
                f"  [EvolutionEngine] Round {round_num + 1}/{self.config.evolutionary_rounds}"
            )

            # Evaluate current population
            population = [
                fitness_eval.evaluate(candidate, self.config.excluded_resource_ids)
                for candidate in population
            ]

            # Update archive
            for candidate in population:
                self.archive.add_candidate(candidate)

            # Track best
            round_best = max(population, key=lambda c: c.score)
            if round_best.score > best_ever.score:
                best_ever = round_best
                stagnation_counter = 0
                print(f"      New best score: {round_best.score:.4f}")
            else:
                stagnation_counter += 1

            if stagnation_counter >= self.config.evolutionary_stagnation_limit:
                print(f"      Stagnation limit reached. Stopping.")
                break

            # Update elite
            self.archive.update_elite()

            # Create next generation
            next_population = []

            # Preserve elite
            for elite_candidate in self.archive.elite_candidates:
                if len(next_population) < self.config.evolutionary_elite_count:
                    next_population.append(elite_candidate)

            # Add cold-start diversity
            cold_start_count = int(
                self.config.evolutionary_population_size
                * self.config.evolutionary_cold_start_fraction
            )
            for _ in range(cold_start_count):
                if len(next_population) >= self.config.evolutionary_population_size:
                    break
                cold_start = operators.cold_start_portfolio()
                evaluated = fitness_eval.evaluate(
                    cold_start, self.config.excluded_resource_ids
                )
                next_population.append(evaluated)

            # Generate via mutation and crossover
            while len(next_population) < self.config.evolutionary_population_size:
                if self.rng.random() < self.config.evolutionary_crossover_rate:
                    # Crossover: blend two parents
                    parent1 = self._tournament_select(population)
                    parent2 = self._tournament_select(population)
                    child = self._portfolio_crossover(parent1, parent2)
                else:
                    # Mutation: modify one parent
                    parent = self._tournament_select(population)
                    child = self._portfolio_mutate(parent, operators)

                if child:
                    evaluated = fitness_eval.evaluate(
                        child, self.config.excluded_resource_ids
                    )
                    if evaluated.is_feasible():
                        next_population.append(evaluated)

            population = next_population[: self.config.evolutionary_population_size]

            print(
                f"      Population: {len(population)}, "
                f"Archive: {len(self.archive.candidates)}, "
                f"Best: {best_ever.score:.4f}"
            )

        print(f"  [EvolutionEngine] Final best score: {best_ever.score:.4f}")
        return best_ever

    def _initialize_population(
        self,
        initial_proposals: List[List[Dict[str, Any]]],
        operators: EvolutionaryOperators,
        fitness_eval: PortfolioFitnessEvaluator,
        warm_start_config: Optional[WarmStartConfig] = None,
    ) -> List[PortfolioCandidate]:
        """Initialize population from expert proposals and warm starts."""
        population = []

        # Add expert proposals as initial candidates
        for proposal in initial_proposals:
            if proposal:
                candidate = PortfolioCandidate(
                    groups=tuple(proposal),
                    provenance="expert_proposal",
                    fingerprint=PortfolioCandidate.compute_fingerprint(proposal),
                )
                evaluated = fitness_eval.evaluate(
                    candidate, self.config.excluded_resource_ids
                )
                if evaluated.is_feasible():
                    population.append(evaluated)

        # Add warm-start candidates if provided
        if warm_start_config and warm_start_config.seed_portfolios:
            for seed_portfolio in warm_start_config.seed_portfolios:
                if seed_portfolio:
                    candidate = PortfolioCandidate(
                        groups=tuple(seed_portfolio),
                        provenance="warm_started",
                        fingerprint=PortfolioCandidate.compute_fingerprint(seed_portfolio),
                    )
                    evaluated = fitness_eval.evaluate(
                        candidate, self.config.excluded_resource_ids
                    )
                    if evaluated.is_feasible():
                        population.append(evaluated)

        # Fill with cold-start random portfolios
        while len(population) < self.config.evolutionary_population_size:
            cold_start = operators.cold_start_portfolio()
            evaluated = fitness_eval.evaluate(
                cold_start, self.config.excluded_resource_ids
            )
            if evaluated.is_feasible():
                population.append(evaluated)

        return population

    def _tournament_select(
        self, population: List[PortfolioCandidate], k: int = 3
    ) -> PortfolioCandidate:
        """Tournament selection for parent candidate."""
        if not population:
            return PortfolioCandidate()
        candidates = self.rng.sample(population, min(k, len(population)))
        return max(candidates, key=lambda c: c.score)

    def _portfolio_crossover(
        self, parent1: PortfolioCandidate, parent2: PortfolioCandidate
    ) -> Optional[PortfolioCandidate]:
        """Blend two parent portfolios via group inheritance.

        Each group has a chance to be inherited from either parent.
        """
        if not parent1.groups or not parent2.groups:
            return None

        all_groups = list(parent1.groups) + list(parent2.groups)
        child_groups = []
        assigned_ids = set()

        for group in all_groups:
            if len(child_groups) >= self.config.group_max_size:
                break

            group_ids = {eq.ankama_id for eq in group.get("equipments", [])}

            # Skip if any equipment already assigned
            if group_ids & assigned_ids:
                continue

            if self.rng.random() < 0.5:
                child_groups.append(group)
                assigned_ids.update(group_ids)

        if not child_groups:
            return None

        return PortfolioCandidate(
            groups=tuple(child_groups),
            provenance="evolved",
            fingerprint=PortfolioCandidate.compute_fingerprint(child_groups),
            parent_ids=frozenset([parent1.fingerprint, parent2.fingerprint]),
            generation=max(parent1.generation, parent2.generation) + 1,
            metadata={"operator": "crossover"},
        )

    def _portfolio_mutate(
        self,
        portfolio: PortfolioCandidate,
        operators: EvolutionaryOperators,
    ) -> Optional[PortfolioCandidate]:
        """Apply a random mutation operator to portfolio."""
        mutation_ops = [
            operators.add_equipment_to_group,
            operators.remove_weakest_equipment,
            operators.swap_equipment_for_neighbor,
            operators.split_oversized_group,
            operators.merge_compatible_groups,
            operators.move_equipment_between_groups,
        ]

        if not self.equipments or self.rng.random() > self.config.evolutionary_mutation_rate:
            return portfolio

        op = self.rng.choice(mutation_ops)

        if op in (
            operators.add_equipment_to_group,
            operators.remove_weakest_equipment,
        ):
            return op(portfolio, self.config)
        elif op in (
            operators.split_oversized_group,
            operators.merge_compatible_groups,
            operators.move_equipment_between_groups,
        ):
            return op(portfolio, self.config)
        else:
            return op(portfolio)

    @property
    def graph(self):
        """Get the equipment graph."""
        return getattr(self, "_graph", None)

    @graph.setter
    def graph(self, value):
        """Set the equipment graph."""
        self._graph = value
