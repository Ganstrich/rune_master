"""Genetic algorithm-based grouping expert.

Uses evolutionary strategies (selection, crossover, mutation) to evolve 
optimal equipment groups by maximizing a global fitness function.
"""

import random
from typing import List, Dict, Any, Optional, Set
from models import Equipment
from processing.experts.base import GroupingExpert
from processing.config_dataclass import ProcessingConfig
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
        population_size: int = 20,
        generations: int = 30,
        mutation_rate: float = 0.2
    ):
        super().__init__("GeneticExpert", cache_manager, api_client)
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate

    def discover_groups(
        self, 
        equipments: List[Equipment], 
        config: ProcessingConfig
    ) -> List[Dict[str, Any]]:
        """Run the genetic discovery pipeline."""
        if not equipments:
            return []

        try:
            print(f"      [{self.name}] Initializing population (size: {self.population_size})...")
            
            # 1. Initial Population: Mixture of random and seed-based individuals
            population = self._initialize_population(equipments, config)
            
            if not population:
                print(f"      [{self.name}] ⚠️ Failed to initialize population.")
                return []

            # 2. Evolution Loop
            for gen in range(self.generations):
                # Evaluate fitness
                fitness_scores = [self._calculate_individual_fitness(ind) for ind in population]
                
                # Selection (Tournament)
                new_population = []
                for _ in range(self.population_size // 2):
                    parent1 = self._select(population, fitness_scores)
                    parent2 = self._select(population, fitness_scores)
                    
                    # Crossover
                    child1, child2 = self._crossover(parent1, parent2)
                    
                    # Mutation
                    self._mutate(child1, equipments)
                    self._mutate(child2, equipments)
                    
                    # Ensure children are not empty
                    if child1: new_population.append(child1)
                    if child2: new_population.append(child2)
                
                # Refill if needed
                while len(new_population) < self.population_size:
                    new_population.append(self._create_random_individual(equipments, config))
                
                population = new_population[:self.population_size]
                
                if (gen + 1) % 10 == 0:
                    best_fit = max(fitness_scores)
                    print(f"      [{self.name}] Generation {gen+1}/{self.generations} - Best Fitness: {best_fit:.2f}")

            # 3. Extract best individual
            final_fitness = [self._calculate_individual_fitness(ind) for ind in population]
            best_individual = population[final_fitness.index(max(final_fitness))]
            
            # 4. Convert best individual to standardized Group format
            mapper = GroupMapper(equipments, excluded_resource_ids=config.excluded_resource_ids)
            
            # Our individual is a list of sets of equipments
            final_groups = []
            for eq_set in best_individual:
                if len(eq_set) < config.group_min_size:
                    continue
                    
                # Use GroupMapper to get full metadata (efficiency, ingredients, etc.)
                group_data = mapper.create_group(
                    list(eq_set),
                    cache_manager=self.cache_manager,
                    api_client=self.api_client
                )
                
                if group_data.get("sharing_efficiency", 0) >= config.group_efficiency_threshold:
                    group_data["expert_name"] = self.name
                    group_data["selection_method"] = "genetic"
                    final_groups.append(group_data)
                    
            return final_groups
        except Exception as e:
            print(f"      [{self.name}] ❌ Expert failed internally: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _initialize_population(self, equipments: List[Equipment], config: ProcessingConfig) -> List[List[Set[Equipment]]]:
        """Create initial diverse individuals."""
        population = []
        for _ in range(self.population_size):
            population.append(self._create_random_individual(equipments, config))
        return population

    def _create_random_individual(self, equipments: List[Equipment], config: ProcessingConfig) -> List[Set[Equipment]]:
        """Create a single random individual."""
        individual = []
        num_groups = random.randint(3, 8)
        available = list(equipments)
        random.shuffle(available)
        
        for _ in range(num_groups):
            if not available: break
            size = random.randint(config.group_min_size, config.group_max_size)
            group_set = set(available[:size])
            available = available[size:]
            if group_set:
                individual.append(group_set)
        return individual

    def _calculate_individual_fitness(self, individual: List[Set[Equipment]]) -> float:
        """Fitness = Sum(Efficiency * Size) - Overlap Penalty."""
        total_score = 0.0
        seen_ids = set()
        overlap_penalty = 0.0
        
        if not individual:
            return -100.0

        for eq_set in individual:
            if not eq_set: continue
            
            # Calculate efficiency roughly for fitness (to avoid full GroupMapper overhead)
            all_resources = []
            for eq in eq_set:
                # Use defensive logic similar to GroupMapper
                if hasattr(eq, 'recipe') and eq.recipe:
                    all_resources.extend([r.resource_id for r in eq.recipe if hasattr(r, 'resource_id')])
            
            if not all_resources: continue
            
            unique_resources = set(all_resources)
            efficiency = len(unique_resources) / len(all_resources) 
            
            # Fitness wants LOW unique/total ratio, so (1 - ratio) * size
            sharing_score = (1.0 - efficiency) * len(eq_set)
            total_score += sharing_score
            
            # Overlap penalty
            for eq in eq_set:
                if eq.ankama_id in seen_ids:
                    overlap_penalty += 1.0 # Stronger penalty for redundancy
                seen_ids.add(eq.ankama_id)
                
        return total_score - overlap_penalty

    def _select(self, population: List[Any], scores: List[float]) -> Any:
        """Tournament selection."""
        if not population: return []
        idx1, idx2 = random.sample(range(len(population)), 2)
        return population[idx1] if scores[idx1] > scores[idx2] else population[idx2]

    def _crossover(self, p1: List[Set[Equipment]], p2: List[Set[Equipment]]) -> tuple:
        """Exchange groups between parents."""
        if not p1: return [], p2[:]
        if not p2: return p1[:], []
        
        cp = random.randint(0, min(len(p1), len(p2)))
        c1 = p1[:cp] + p2[cp:]
        c2 = p2[:cp] + p1[cp:]
        return c1, c2

    def _mutate(self, individual: List[Set[Equipment]], all_equipments: List[Equipment]):
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
                individual.pop(idx) # Remove group if it becomes too small
        
        elif mutation_type == "merge" and len(individual) >= 2:
            i1, i2 = random.sample(range(len(individual)), 2)
            individual[i1].update(individual[i2])
            individual.pop(i2)
