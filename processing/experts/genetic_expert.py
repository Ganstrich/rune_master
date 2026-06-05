"""Genetic algorithm-based grouping expert.

Uses evolutionary strategies (selection, crossover, mutation) to evolve
optimal equipment groups by maximizing a global fitness function.
"""

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from models import Equipment
from processing.config_dataclass import ProcessingConfig
from processing.experts.base import GroupingExpert
from processing.group_mapper import GroupMapper


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
    ):
        super().__init__("GeneticExpert", cache_manager, api_client)
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_count = elite_count
        self.stagnation_limit = stagnation_limit

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
                    min_shared_count=config.graph_min_shared_count,
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

            # 2. Evolution Loop
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
                    parent1 = self._tournament_select(population, fitness_scores)
                    parent2 = self._tournament_select(population, fitness_scores)

                    child1, child2 = self._crossover(parent1, parent2, resource_sets)

                    self._mutate(child1, graph, eq_by_id, resource_sets, config)
                    self._mutate(child2, graph, eq_by_id, resource_sets, config)

                    if child1:
                        new_population.append(child1)
                    if child2 and len(new_population) < self.population_size:
                        new_population.append(child2)

                population = new_population[: self.population_size]

                if (gen + 1) % 10 == 0:
                    best_fit = max(fitness_scores)
                    print(
                        f"      [{self.name}] Generation {gen + 1}/{self.generations} - Best Fitness: {best_fit:.2f}"
                    )

            # 3. Extract best individual
            final_fitness = [
                self._calculate_individual_fitness(ind) for ind in population
            ]
            best_individual = population[final_fitness.index(max(final_fitness))]

            # 4. Convert best individual to standardized Group format
            mapper = GroupMapper(
                equipments, excluded_resource_ids=config.excluded_resource_ids
            )

            # Our individual is a list of sets of equipments
            final_groups = []
            for eq_set in best_individual:
                if len(eq_set) < config.group_min_size:
                    continue

                # Use GroupMapper to get full metadata (efficiency, ingredients, etc.)
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

            return final_groups
        except Exception as e:
            print(f"      [{self.name}] ❌ Expert failed internally: {e}")
            import traceback

            traceback.print_exc()
            return []

    def _initialize_population(
        self, equipments: List[Equipment], config: ProcessingConfig
    ) -> List[List[Set[Equipment]]]:
        """Create initial diverse individuals."""
        population = []
        for _ in range(self.population_size):
            population.append(self._create_random_individual(equipments, config))
        return population

    def _create_random_individual(
        self, equipments: List[Equipment], config: ProcessingConfig
    ) -> List[Set[Equipment]]:
        """Create a single random individual."""
        individual = []
        num_groups = random.randint(3, 8)
        available = list(equipments)
        random.shuffle(available)

        for _ in range(num_groups):
            if not available:
                break
            size = random.randint(config.group_min_size, config.group_max_size)
            group_set = set(available[:size])
            available = available[size:]
            if group_set:
                individual.append(group_set)
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
        seen_ids = set()
        overlap_penalty = 0.0

        if not individual:
            return -100.0

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
                    overlap_penalty += 1.0  # Stronger penalty for redundancy
                seen_ids.add(eq.ankama_id)

        return total_score - overlap_penalty

    @staticmethod
    def _equipment_group_affinity(
        eq_id: int, group_ids: Set[int], resource_sets: Dict[int, Set[int]]
    ) -> float:
        """Measure how well an equipment fits in a group by resource overlap."""
        eq_resources = resource_sets.get(eq_id, set())
        if not eq_resources or not group_ids:
            return 0.0
        group_resources: Set[int] = set()
        for gid in group_ids:
            group_resources |= resource_sets.get(gid, set())
        if not group_resources:
            return 0.0
        return len(eq_resources & group_resources) / len(eq_resources | group_resources)

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
        self,
        p1: List[Set[Equipment]],
        p2: List[Set[Equipment]],
        resource_sets: Dict[int, Set[int]],
    ) -> Tuple[List[Set[Equipment]], List[Set[Equipment]]]:
        """Group-based crossover: assign parent groups to children, resolve conflicts.

        Algorithm:
        1. Collect all groups from both parents into a pool
        2. For each group, randomly assign to child1, child2, or both
        3. Resolve conflicts (equipment in multiple groups within same child)
           by keeping it in the group where it has higher affinity
        4. Remove groups that fall below config.group_min_size after resolution
        """
        # Build group pool with parent labels for tracking
        all_groups: List[Tuple[Set[Equipment], int]] = []
        for g in p1:
            all_groups.append((g.copy(), 0))
        for g in p2:
            all_groups.append((g.copy(), 1))

        # Assign groups to children
        child1_groups: List[Set[Equipment]] = []
        child2_groups: List[Set[Equipment]] = []

        for group, _ in all_groups:
            assignment = random.choice(["c1", "c2", "both"])
            if assignment in ("c1", "both"):
                child1_groups.append(group.copy())
            if assignment in ("c2", "both"):
                child2_groups.append(group.copy())

        # Resolve conflicts in each child
        child1_groups = self._resolve_conflicts(child1_groups, resource_sets)
        child2_groups = self._resolve_conflicts(child2_groups, resource_sets)

        return child1_groups, child2_groups

    def _resolve_conflicts(
        self,
        groups: List[Set[Equipment]],
        resource_sets: Dict[int, Set[int]],
    ) -> List[Set[Equipment]]:
        """Resolve equipment appearing in multiple groups within a child.

        For each conflicting equipment, keep it in the group where it has
        the highest affinity (resource overlap), and remove it from others.
        """
        if not groups:
            return groups

        # Build equipment -> list of group indices map
        eq_to_groups: Dict[int, List[int]] = {}
        for i, group in enumerate(groups):
            for eq in group:
                eq_to_groups.setdefault(eq.ankama_id, []).append(i)

        # Find conflicts (equipment in > 1 group)
        conflicts = {
            eq_id: g_indices
            for eq_id, g_indices in eq_to_groups.items()
            if len(g_indices) > 1
        }

        if not conflicts:
            return groups

        # Resolve each conflict
        for eq_id, g_indices in conflicts.items():
            # Find the equipment object
            eq_obj = None
            for i in g_indices:
                for eq in groups[i]:
                    if eq.ankama_id == eq_id:
                        eq_obj = eq
                        break
                if eq_obj:
                    break

            if not eq_obj:
                continue

            # Calculate affinity for each group
            best_group_idx = g_indices[0]
            best_affinity = -1.0

            for i in g_indices:
                group_ids = {e.ankama_id for e in groups[i]}
                affinity = self._equipment_group_affinity(
                    eq_id, group_ids, resource_sets
                )
                if affinity > best_affinity:
                    best_affinity = affinity
                    best_group_idx = i

            # Remove from all groups except the best one
            for i in g_indices:
                if i != best_group_idx:
                    groups[i] = {eq for eq in groups[i] if eq.ankama_id != eq_id}

        return groups

    def _mutate(
        self, individual: List[Set[Equipment]], all_equipments: List[Equipment]
    ):
        """Mutate individual: move item, add item, or merge groups."""
        if random.random() > self.mutation_rate or not individual:
            return

        mutation_type = random.choice(["add", "remove", "merge"])

        if mutation_type == "add":
            idx = random.randint(0, len(individual) - 1)
            new_eq = random.choice(all_equipments)
            individual[idx].add(new_eq)

        elif mutation_type == "remove":
            idx = random.randint(0, len(individual) - 1)
            if len(individual[idx]) > 1:
                individual[idx].pop()
            else:
                individual.pop(idx)  # Remove group if it becomes too small

        elif mutation_type == "merge" and len(individual) >= 2:
            i1, i2 = random.sample(range(len(individual)), 2)
            individual[i1].update(individual[i2])
            individual.pop(i2)
