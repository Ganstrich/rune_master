"""Genetic algorithm-based grouping expert.

Uses evolutionary strategies (selection, crossover, mutation) to evolve
optimal equipment groups. Builds a similarity graph first, then evolves
partitions of that graph using sharing_efficiency as the fitness metric.
"""

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from models import Equipment
from processing.config_dataclass import ProcessingConfig
from processing.experts.base import GroupingExpert
from processing.graph_builder import GraphBuilder
from processing.group_mapper import GroupMapper


class GeneticGroupingExpert(GroupingExpert):
    """Expert that uses Genetic Algorithms to discover optimal groups.

    Builds an equipment similarity graph, then evolves graph-aware partitions.
    Uses the same sharing_efficiency metric as GroupMapper for consistency.
    """

    def __init__(
        self,
        cache_manager: Optional[Any] = None,
        api_client: Optional[Any] = None,
        population_size: int = 30,
        generations: int = 50,
        mutation_rate: float = 0.3,
        elite_count: int = 3,
    ):
        super().__init__("GeneticExpert", cache_manager, api_client)
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_count = elite_count

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

        try:
            # 1. Build similarity graph to identify candidate neighbors
            print(f"      [{self.name}] Building equipment similarity graph...")
            if precomputed_graph is not None and precomputed_resources is not None:
                graph = precomputed_graph
                equipment_resources = precomputed_resources
            else:
                graph, equipment_resources = GraphBuilder.build_equipment_graph(
                    equipments,
                    min_shared_ratio=config.graph_min_shared_ratio,
                    min_shared_count=config.group_min_shared_resources,
                    min_component_size=config.graph_min_component_size,
                )

            if graph.number_of_nodes() == 0:
                print(f"      [{self.name}] ⚠️ No connected equipment found.")
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
            population = self._initialize_population(
                graph, eq_by_id, resource_sets, config
            )

            if not population:
                print(f"      [{self.name}] ⚠️ Failed to initialize population.")
                return []

            # 3. Evolution Loop
            best_ever_fitness = -1.0
            best_ever_individual = None
            stagnation_counter = 0

            for gen in range(self.generations):
                # Evaluate fitness
                fitness_scores = [
                    self._calculate_individual_fitness(ind, resource_sets, config)
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

                # Elitism: carry forward top individuals
                ranked = sorted(
                    zip(population, fitness_scores), key=lambda x: x[1], reverse=True
                )
                new_population = [ind.copy() for ind, _ in ranked[: self.elite_count]]

                # Fill rest with crossover + mutation
                while len(new_population) < self.population_size:
                    parent1 = self._tournament_select(population, fitness_scores)
                    parent2 = self._tournament_select(population, fitness_scores)

                    child1, child2 = self._crossover(parent1, parent2)

                    self._mutate(child1, graph, eq_by_id, resource_sets, config)
                    self._mutate(child2, graph, eq_by_id, resource_sets, config)

                    if child1:
                        new_population.append(child1)
                    if child2 and len(new_population) < self.population_size:
                        new_population.append(child2)

                population = new_population[: self.population_size]

                if (gen + 1) % 10 == 0:
                    print(
                        f"      [{self.name}] Generation {gen + 1}/{self.generations}"
                        f" - Best: {gen_best_fitness:.3f}"
                        f" (ever: {best_ever_fitness:.3f})"
                    )

            # 4. Use best individual ever seen
            if best_ever_individual is None:
                final_fitness = [
                    self._calculate_individual_fitness(ind, resource_sets, config)
                    for ind in population
                ]
                best_idx = max(
                    range(len(final_fitness)), key=lambda i: final_fitness[i]
                )
                best_individual = population[best_idx]
            else:
                best_individual = best_ever_individual

            # 5. Convert to standardized Group format
            mapper = GroupMapper(
                equipments, excluded_resource_ids=config.excluded_resource_ids
            )

            final_groups = []
            seen_equipment_ids: Set[int] = set()
            for eq_set in best_individual:
                if len(eq_set) < config.group_min_size:
                    continue

                # Skip groups that overlap with already-selected groups
                eq_ids = {eq.ankama_id for eq in eq_set}
                if eq_ids & seen_equipment_ids:
                    continue

                group_data = mapper.create_group(
                    list(eq_set),
                    cache_manager=self.cache_manager,
                    api_client=self.api_client,
                )

                if (
                    group_data.get("sharing_efficiency", 0)
                    >= config.group_efficiency_threshold
                ):
                    group_data["expert_name"] = self.name
                    group_data["selection_method"] = "genetic"
                    final_groups.append(group_data)
                    seen_equipment_ids |= eq_ids

            print(
                f"      [{self.name}] Produced {len(final_groups)} groups"
                f" (avg efficiency: {sum(g['sharing_efficiency'] for g in final_groups) / len(final_groups):.3f})"
                if final_groups
                else f"      [{self.name}] No groups passed efficiency threshold."
            )
            return final_groups

        except Exception as e:
            print(f"      [{self.name}] ❌ Expert failed internally: {e}")
            import traceback

            traceback.print_exc()
            return []

    def _initialize_population(
        self,
        graph,
        eq_by_id: Dict[int, Equipment],
        resource_sets: Dict[int, Set[int]],
        config: ProcessingConfig,
    ) -> List[List[Set[Equipment]]]:
        """Create initial diverse individuals using graph-aware seeding.

        Half the population is seeded from graph neighbors (high-quality),
        the other half is random for diversity.
        """
        population: List[List[Set[Equipment]]] = []
        graph_nodes = list(graph.nodes())
        num_groups_target = max(3, len(graph_nodes) // (config.group_max_size + 1))

        for i in range(self.population_size):
            if i < self.population_size // 2:
                # Graph-aware seeding: pick random seeds, grow via neighbors
                individual = self._create_graph_seeded_individual(
                    graph,
                    graph_nodes,
                    eq_by_id,
                    resource_sets,
                    config,
                    num_groups_target,
                )
            else:
                # Random individual for diversity
                individual = self._create_random_individual(
                    graph_nodes, eq_by_id, config
                )
            if individual:
                population.append(individual)

        return population

    def _create_graph_seeded_individual(
        self,
        graph,
        graph_nodes: List[int],
        eq_by_id: Dict[int, Equipment],
        resource_sets: Dict[int, Set[int]],
        config: ProcessingConfig,
        num_groups: int,
    ) -> List[Set[Equipment]]:
        """Create an individual by growing groups from random seed nodes.

        Each seed expands to include its most similar neighbors, creating
        groups with inherently high sharing potential.
        """
        individual: List[Set[Equipment]] = []
        used_ids: Set[int] = set()
        seeds = random.sample(graph_nodes, min(num_groups, len(graph_nodes)))

        for seed_id in seeds:
            if seed_id in used_ids:
                continue

            group_ids: Set[int] = {seed_id}
            candidates = list(graph.neighbors(seed_id))
            random.shuffle(candidates)

            # Grow group by adding neighbors that share the most resources
            # with current group members
            while len(group_ids) < config.group_max_size and candidates:
                # Score each candidate by shared resources with current group
                best_candidate = None
                best_shared = -1
                for c in candidates:
                    if c in used_ids or c in group_ids:
                        continue
                    c_resources = resource_sets.get(c, set())
                    group_resources: Set[int] = set()
                    for gid in group_ids:
                        group_resources |= resource_sets.get(gid, set())
                    shared = len(c_resources & group_resources)
                    if shared > best_shared:
                        best_shared = shared
                        best_candidate = c

                if best_candidate is None or best_shared == 0:
                    break

                group_ids.add(best_candidate)
                candidates = [
                    n
                    for n in graph.neighbors(best_candidate)
                    if n not in used_ids and n not in group_ids
                ]

            if len(group_ids) >= config.group_min_size:
                group = {eq_by_id[eid] for eid in group_ids if eid in eq_by_id}
                if group:
                    individual.append(group)
                    used_ids |= group_ids

        return individual

    def _create_random_individual(
        self,
        graph_nodes: List[int],
        eq_by_id: Dict[int, Equipment],
        config: ProcessingConfig,
    ) -> List[Set[Equipment]]:
        """Create a random individual from graph nodes."""
        individual: List[Set[Equipment]] = []
        available = [n for n in graph_nodes if n in eq_by_id]
        random.shuffle(available)

        num_groups = random.randint(2, max(3, len(available) // config.group_max_size))
        for _ in range(num_groups):
            if not available:
                break
            size = random.randint(config.group_min_size, config.group_max_size)
            group_ids = set(available[:size])
            available = available[size:]
            group = {eq_by_id[eid] for eid in group_ids}
            if group:
                individual.append(group)
        return individual

    def _calculate_individual_fitness(
        self,
        individual: List[Set[Equipment]],
        resource_sets: Dict[int, Set[int]],
        config: Optional[ProcessingConfig] = None,
    ) -> float:
        """Fitness = Sum(group_sharing_efficiency) - Overlap Penalty.

        Uses the canonical "2+" sharing_efficiency definition:
            shared_count / total_unique
        where shared_count = resources used by >= 2 equipment in the group,
        and total_unique = union of all resources in the group.

        This is size-independent (0-1 range per group), so the fitness
        rewards sharing density rather than raw group size.
        """
        total_score = 0.0
        seen_ids: Set[int] = set()
        overlap_penalty = 0.0

        if not individual:
            return -100.0

        min_size = config.group_min_size if config else 2

        for eq_set in individual:
            if not eq_set:
                continue

            if len(eq_set) < min_size:
                continue

            # Count how many equipment use each resource
            resource_usage: Dict[int, int] = {}
            all_unique: Set[int] = set()
            for eq in eq_set:
                rset = resource_sets.get(eq.ankama_id, set())
                for r in rset:
                    resource_usage[r] = resource_usage.get(r, 0) + 1
                all_unique |= rset

            total_unique = len(all_unique)
            if total_unique == 0:
                continue

            # Shared = resources used by >= 2 equipment
            shared_count = sum(1 for count in resource_usage.values() if count >= 2)

            sharing_efficiency = shared_count / total_unique
            total_score += sharing_efficiency

            # Overlap penalty
            for eq in eq_set:
                if eq.ankama_id in seen_ids:
                    overlap_penalty += 1.0
                seen_ids.add(eq.ankama_id)

        return total_score - overlap_penalty

    def _tournament_select(
        self, population: List[Any], scores: List[float], k: int = 3
    ) -> Any:
        """Tournament selection with configurable tournament size."""
        if not population:
            return []
        candidates = random.sample(range(len(population)), min(k, len(population)))
        best = max(candidates, key=lambda i: scores[i])
        return population[best]

    def _crossover(
        self, p1: List[Set[Equipment]], p2: List[Set[Equipment]]
    ) -> Tuple[List[Set[Equipment]], List[Set[Equipment]]]:
        """Exchange groups between parents, resolving conflicts."""
        if not p1:
            return [], [s.copy() for s in p2]
        if not p2:
            return [s.copy() for s in p1], []

        # Use equipment-level crossover: each equipment goes to the child
        # group that has more of its neighbors
        p1_ids = set()
        for g in p1:
            p1_ids.update(eq.ankama_id for eq in g)
        p2_ids = set()
        for g in p2:
            p2_ids.update(eq.ankama_id for eq in g)

        # Only crossover on shared equipment IDs
        common_ids = p1_ids & p2_ids
        if not common_ids:
            return [s.copy() for s in p1], [s.copy() for s in p2]

        # Build ID -> group index maps
        p1_map: Dict[int, int] = {}
        for i, g in enumerate(p1):
            for eq in g:
                p1_map[eq.ankama_id] = i
        p2_map: Dict[int, int] = {}
        for i, g in enumerate(p2):
            for eq in g:
                p2_map[eq.ankama_id] = i

        # For each common ID, randomly assign to child1 or child2
        child1_groups: Dict[int, Set[Equipment]] = {}
        child2_groups: Dict[int, Set[Equipment]] = {}

        for eq_id in common_ids:
            eq_p1 = p1_map.get(eq_id)
            eq_p2 = p2_map.get(eq_id)
            if eq_p1 is None or eq_p2 is None:
                continue

            eq_obj = None
            for eq in p1[eq_p1]:
                if eq.ankama_id == eq_id:
                    eq_obj = eq
                    break
            if eq_obj is None:
                continue

            if random.random() < 0.5:
                child1_groups.setdefault(eq_p1, set()).add(eq_obj)
                child2_groups.setdefault(eq_p2, set()).add(eq_obj)
            else:
                child1_groups.setdefault(eq_p2, set()).add(eq_obj)
                child2_groups.setdefault(eq_p1, set()).add(eq_obj)

        # Add non-common IDs from respective parents
        for i, g in enumerate(p1):
            for eq in g:
                if eq.ankama_id not in common_ids:
                    child1_groups.setdefault(i, set()).add(eq)
        for i, g in enumerate(p2):
            for eq in g:
                if eq.ankama_id not in common_ids:
                    child2_groups.setdefault(i + len(p1), set()).add(eq)

        c1 = [g for g in child1_groups.values() if g]
        c2 = [g for g in child2_groups.values() if g]
        return c1, c2

    def _mutate(
        self,
        individual: List[Set[Equipment]],
        graph,
        eq_by_id: Dict[int, Equipment],
        resource_sets: Dict[int, Set[int]],
        config: ProcessingConfig,
    ):
        """Mutate individual using graph-aware operations."""
        if random.random() > self.mutation_rate or not individual:
            return

        mutation_type = random.choice(["add_neighbor", "remove", "split", "swap"])

        if mutation_type == "add_neighbor":
            # Add a graph neighbor of an existing group member
            idx = random.randint(0, len(individual) - 1)
            group_ids = {eq.ankama_id for eq in individual[idx]}
            neighbors = set()
            for eid in group_ids:
                neighbors.update(graph.neighbors(eid))
            neighbors -= group_ids
            # Filter to valid equipment IDs
            neighbors = {n for n in neighbors if n in eq_by_id}
            if neighbors and len(individual[idx]) < config.group_max_size:
                best = max(
                    neighbors,
                    key=lambda n: len(
                        resource_sets.get(n, set())
                        & set().union(
                            *(resource_sets.get(eid, set()) for eid in group_ids)
                        )
                    ),
                )
                individual[idx].add(eq_by_id[best])

        elif mutation_type == "remove":
            idx = random.randint(0, len(individual) - 1)
            if len(individual[idx]) > config.group_min_size:
                # Remove the member with least shared resources
                group_ids = {eq.ankama_id for eq in individual[idx]}
                group_shared: Set[int] = set()
                for eid in group_ids:
                    group_shared |= resource_sets.get(eid, set())
                # Find member whose removal least hurts sharing
                worst_eq = min(
                    individual[idx],
                    key=lambda eq: len(
                        resource_sets.get(eq.ankama_id, set()) & group_shared
                    ),
                )
                individual[idx].remove(worst_eq)
            elif len(individual[idx]) == config.group_min_size:
                # Remove the entire small group
                individual.pop(idx)

        elif (
            mutation_type == "split"
            and len(individual[idx := random.randint(0, len(individual) - 1)])
            > config.group_min_size * 2
        ):
            # Split a large group into two
            members = list(individual[idx])
            random.shuffle(members)
            mid = len(members) // 2
            individual[idx] = set(members[:mid])
            individual.append(set(members[mid:]))

        elif mutation_type == "swap" and len(individual) >= 2:
            # Swap a member between two groups
            i1, i2 = random.sample(range(len(individual)), 2)
            if individual[i1] and individual[i2]:
                eq1 = random.choice(list(individual[i1]))
                eq2 = random.choice(list(individual[i2]))
                individual[i1].discard(eq1)
                individual[i1].add(eq2)
                individual[i2].discard(eq2)
                individual[i2].add(eq1)
