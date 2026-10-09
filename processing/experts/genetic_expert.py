"""Genetic algorithm-based grouping expert.

Uses evolutionary strategies (selection, crossover, mutation) to evolve 
optimal equipment groups by maximizing a global fitness function.
"""

import random
from typing import Any, Dict, List, Optional, Set

from models import Equipment
from processing.config_dataclass import ProcessingConfig
from processing.experts.base import GroupingExpert
from processing.experts.genetic_operators import (
    create_graph_individual,
    crossover,
    initialize_population,
    mutate,
    tournament_select,
)
from processing.graph_builder import GraphBuilder
from processing.group_mapper import GroupMapper
from processing.group_metrics import GroupMetrics
from processing.policy import GroupAcceptancePolicy
from processing.valuation.objective import GroupCandidate, GroupObjective


class GeneticGroupingExpert(GroupingExpert):
    """Expert that uses Genetic Algorithms to discover optimal groups.
    
    Excellent for 'dense' graphs where traditional community detection 
    struggles due to items sharing many common ingredients.
    """
    
    def __init__(
        self, 
        cache_manager: Optional[Any] = None,
        api_client: Optional[Any] = None,
        population_size: int = 30,
        generations: int = 50,
        mutation_rate: float = 0.3,
        elite_count: int = 3,
        stagnation_limit: int = 15,
        objective: Optional[GroupObjective] = None,
        policy: Optional[GroupAcceptancePolicy] = None,
        initial_groups: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__("GeneticExpert", cache_manager, api_client, objective, policy)
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_count = elite_count
        self.stagnation_limit = stagnation_limit
        self.initial_groups = initial_groups or []
        self.provenance = "newly_discovered"

    def evolve_portfolio(
        self,
        portfolio: List[Dict[str, Any]],
        config: ProcessingConfig,
        objective: Optional[GroupObjective] = None,
    ) -> List[Dict[str, Any]]:
        """Re-evaluate and evolve a stored portfolio under current prices."""
        self.initial_groups = portfolio
        self.provenance = "evolved"
        if objective is not None:
            self.objective = objective
        equipment_by_id = {
            equipment.ankama_id: equipment
            for group in portfolio
            for equipment in group.get("equipments", [])
        }
        return self.discover_groups(list(equipment_by_id.values()), config)

    def discover_groups(
        self,
        equipments: List[Equipment],
        config: ProcessingConfig,
        precomputed_graph: Optional[Any] = None,
        precomputed_resources: Optional[Dict[int, Set[int]]] = None,
    ) -> List[Dict[str, Any]]:
        """Run the genetic discovery pipeline."""
        if not equipments:
            return []

        self.population_size = config.genetic_population_size
        self.generations = config.genetic_generations
        self.mutation_rate = config.genetic_mutation_rate
        self.elite_count = config.genetic_elite_count
        self.stagnation_limit = config.genetic_stagnation_limit

        self.rng = random.Random(config.random_seed)

        # 1. Build similarity graph to identify candidate neighbors
        print(f"      [{self.name}] Building equipment similarity graph...")
        if precomputed_graph is not None and precomputed_resources is not None:
            graph = precomputed_graph
            equipment_resources = precomputed_resources
        else:
            graph, equipment_resources = GraphBuilder.build_equipment_graph(
                equipments,
                min_shared_ratio=config.graph_min_shared_ratio,
                min_shared_count=config.graph_min_shared_count,
                min_component_size=config.graph_min_component_size,
                same_set_edge_discount=config.same_set_edge_discount,
            )

        if graph.number_of_nodes() == 0:
            print(f"      [{self.name}] No connected equipment found.")
            return []

        # Map ankama_id -> Equipment for quick lookup
        eq_by_id = {eq.ankama_id: eq for eq in equipments}

        # Resource sets per equipment (filtered by excluded IDs)
        excluded = config.excluded_resource_ids or set()
        resource_sets: Dict[int, Set[int]] = {}
        for eq_id, neighbors in equipment_resources.items():
            resource_sets[eq_id] = {r for r in neighbors if r not in excluded}

        # 2. Initialize population using graph-aware seeding
        print(
            f"      [{self.name}] Initializing population (size: {self.population_size})..."
        )
        population = initialize_population(
            graph, eq_by_id, config, self.rng, self.objective, excluded,
            self.initial_groups, self.population_size,
        )

        if not population:
            print(f"      [{self.name}] Failed to initialize population.")
            return []

        best_ever_fitness = float("-inf")
        best_ever_individual: List[Set[Equipment]] = []
        stagnation_counter = 0

        # 3. Evolution Loop
        for gen in range(self.generations):
            # Evaluate fitness
            fitness_scores = [
                self._calculate_individual_fitness(ind, config)
                for ind in population
            ]

            # Track best
            gen_best_idx = max(
                range(len(fitness_scores)), key=lambda i: fitness_scores[i]
            )
            gen_best_fitness = fitness_scores[gen_best_idx]
            if gen_best_fitness > best_ever_fitness:
                best_ever_fitness = gen_best_fitness
                best_ever_individual = [s.copy() for s in population[gen_best_idx]]
                stagnation_counter = 0
            else:
                stagnation_counter += 1

            if stagnation_counter >= self.stagnation_limit:
                print(
                    f"      [{self.name}] Early stopping at generation {gen + 1} "
                    f"(stagnation: {stagnation_counter} generations)"
                )
                break

            # Elitism: carry forward top individuals
            ranked = sorted(
                zip(population, fitness_scores), key=lambda x: x[1], reverse=True
            )
            new_population = [ind.copy() for ind, _ in ranked[: self.elite_count]]

            # Fill rest with crossover + mutation
            while len(new_population) < self.population_size:
                parent1 = tournament_select(population, fitness_scores, self.rng)
                parent2 = tournament_select(population, fitness_scores, self.rng)

                child1, child2 = crossover(parent1, parent2, resource_sets, self.rng)

                mutate(child1, graph, eq_by_id, resource_sets, config, self.rng, self.objective, self.mutation_rate)
                mutate(child2, graph, eq_by_id, resource_sets, config, self.rng, self.objective, self.mutation_rate)

                if child1:
                    new_population.append(child1)
                if child2 and len(new_population) < self.population_size:
                    new_population.append(child2)

            population = new_population[: self.population_size]

            if (gen + 1) % 10 == 0:
                best_fit = max(fitness_scores)
                print(f"      [{self.name}] Generation {gen+1}/{self.generations} - Best Fitness: {best_fit:.2f}")

        # 4. Extract best individual
        best_individual = best_ever_individual
            
        # 5. Convert best individual to standardized Group format
        mapper = GroupMapper(
            equipments,
            excluded_resource_ids=config.excluded_resource_ids,
            quality_weights=config.group_quality_weights,
            acceptance_policy=self.policy or GroupAcceptancePolicy(config),
        )
            
        # Our individual is a list of sets of equipments
        final_groups = []
        for eq_set in best_individual:
            # Use GroupMapper to get full metadata (efficiency, ingredients, etc.)
            group_data = mapper.create_group(
                list(eq_set),
                cache_manager=self.cache_manager,
                api_client=self.api_client
            )
                
            if (self.policy or GroupAcceptancePolicy(config)).accepts(group_data):
                group_data["expert_name"] = self.name
                group_data["selection_method"] = "genetic"
                group_data["provenance"] = self.provenance
                final_groups.append(group_data)

        return final_groups

    def _calculate_individual_fitness(
        self,
        individual: List[Set[Equipment]],
        config: ProcessingConfig,
    ) -> float:
        """Fitness = sum(objective group scores) - overlap penalty.

        Uses the canonical "2+" sharing_efficiency definition:
            shared_count / total_unique
        where shared_count = resources used by >= 2 equipment in the group,
        and total_unique = union of all resources in the group.

        This is size-independent (0-1 range per group), so the fitness
        rewards sharing density rather than raw group size.
        """
        total_score = 0.0
        seen_ids = set()
        overlap_penalty = 0.0
        policy = self.policy or (GroupAcceptancePolicy(config) if config is not None else None)
        
        if not individual:
            return -100.0

        for eq_set in individual:
            if not eq_set:
                continue

            group_data = GroupMetrics.build_group_dict(
                list(eq_set), excluded_resource_ids=config.excluded_resource_ids,
                quality_weights=config.group_quality_weights,
            )
            candidate = {
                "equipments": eq_set,
                "group_size": len(eq_set),
                "shared_resources_count": group_data["shared_resources_count"],
                "sharing_efficiency": group_data["sharing_efficiency"],
                "quality_score": group_data["quality_score"],
            }
            if policy is not None and not policy.accepts(candidate):
                continue
            total_score += (
                self.objective.score(
                    GroupCandidate(list(eq_set), config.excluded_resource_ids)
                )
                if self.objective is not None
                else group_data["quality_score"]
            )

            # Overlap penalty
            for eq in eq_set:
                if eq.ankama_id in seen_ids:
                    overlap_penalty += 1.0 # Stronger penalty for redundancy
                seen_ids.add(eq.ankama_id)
                
        return total_score - overlap_penalty
