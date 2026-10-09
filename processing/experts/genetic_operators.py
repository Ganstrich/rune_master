"""Genetic algorithm operators for the genetic grouping expert."""
import random
from typing import Any, Dict, List, Optional, Set, Tuple

from models import Equipment
from processing.config_dataclass import ProcessingConfig
from processing.valuation.objective import GroupObjective


def equipment_group_affinity(
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


def tournament_select(
    population: List[Any], scores: List[float], rng: random.Random, k: int = 3
) -> Any:
    """Tournament selection with configurable tournament size."""
    if not population:
        return []
    candidates = rng.sample(range(len(population)), min(k, len(population)))
    best = max(candidates, key=lambda i: scores[i])
    return population[best]


def resolve_conflicts(
    groups: List[Set[Equipment]],
    resource_sets: Dict[int, Set[int]],
    rng: random.Random,
) -> List[Set[Equipment]]:
    """Resolve equipment appearing in multiple groups within a child.

    For each conflicting equipment, keep it in the group where it has
    the highest affinity (resource overlap), and remove it from others.
    """
    if not groups:
        return groups

    eq_to_groups: Dict[int, List[int]] = {}
    for i, group in enumerate(groups):
        for eq in group:
            eq_to_groups.setdefault(eq.ankama_id, []).append(i)

    conflicts = {
        eq_id: g_indices
        for eq_id, g_indices in eq_to_groups.items()
        if len(g_indices) > 1
    }

    if not conflicts:
        return groups

    for eq_id, g_indices in conflicts.items():
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

        best_group_idx = g_indices[0]
        best_affinity = -1.0

        for i in g_indices:
            group_ids = {e.ankama_id for e in groups[i]}
            affinity = equipment_group_affinity(eq_id, group_ids, resource_sets)
            if affinity > best_affinity:
                best_affinity = affinity
                best_group_idx = i

        for i in g_indices:
            if i != best_group_idx:
                groups[i] = {eq for eq in groups[i] if eq.ankama_id != eq_id}

    return groups


def crossover(
    p1: List[Set[Equipment]],
    p2: List[Set[Equipment]],
    resource_sets: Dict[int, Set[int]],
    rng: random.Random,
) -> Tuple[List[Set[Equipment]], List[Set[Equipment]]]:
    """Group-based crossover: assign parent groups to children, resolve conflicts."""
    all_groups: List[Tuple[Set[Equipment], int]] = []
    for g in p1:
        all_groups.append((g.copy(), 0))
    for g in p2:
        all_groups.append((g.copy(), 1))

    child1_groups: List[Set[Equipment]] = []
    child2_groups: List[Set[Equipment]] = []

    for group, _ in all_groups:
        assignment = rng.choice(["c1", "c2", "both"])
        if assignment in ("c1", "both"):
            child1_groups.append(group.copy())
        if assignment in ("c2", "both"):
            child2_groups.append(group.copy())

    child1_groups = resolve_conflicts(child1_groups, resource_sets, rng)
    child2_groups = resolve_conflicts(child2_groups, resource_sets, rng)

    return child1_groups, child2_groups


def mutate(
    individual: List[Set[Equipment]],
    graph: Any,
    eq_by_id: Dict[int, Equipment],
    resource_sets: Dict[int, Set[int]],
    config: ProcessingConfig,
    rng: random.Random,
    objective: Optional[GroupObjective],
    mutation_rate: float,
) -> None:
    """Mutate individual: move item, add item, or merge groups."""
    if rng.random() > mutation_rate or not individual:
        return

    mutation_type = rng.choice(["add", "remove", "merge"])

    if mutation_type == "add":
        idx = rng.randint(0, len(individual) - 1)
        if len(individual[idx]) >= config.group_max_size:
            return
        assigned_ids = {
            equipment.ankama_id for group in individual for equipment in group
        }
        candidate_ids = {
            neighbor
            for equipment in individual[idx]
            for neighbor in graph.neighbors(equipment.ankama_id)
            if neighbor not in assigned_ids and neighbor in eq_by_id
        }
        if candidate_ids:
            candidates = [eq_by_id[candidate_id] for candidate_id in candidate_ids]
            if objective is None:
                selected = rng.choice(candidates)
            else:
                from processing.valuation.objective import GroupCandidate
                current = GroupCandidate(
                    list(individual[idx]), config.excluded_resource_ids
                )
                selected = max(
                    candidates,
                    key=lambda candidate: objective.marginal(current, candidate),
                )
            individual[idx].add(selected)

    elif mutation_type == "remove":
        idx = rng.randint(0, len(individual) - 1)
        if len(individual[idx]) > config.group_min_size:
            individual[idx].pop()

    elif mutation_type == "merge" and len(individual) >= 2:
        i1, i2 = rng.sample(range(len(individual)), 2)
        if len(individual[i1] | individual[i2]) <= config.group_max_size:
            individual[i1].update(individual[i2])
            individual.pop(i2)


def create_graph_individual(
    graph: Any,
    eq_by_id: Dict[int, Equipment],
    config: ProcessingConfig,
    rng: random.Random,
    objective: Optional[GroupObjective],
    excluded_resource_ids: Set[int],
) -> List[Set[Equipment]]:
    """Create one candidate from high-affinity graph neighborhoods."""
    from processing.valuation.objective import GroupCandidate
    individual: List[Set[Equipment]] = []
    available = set(graph.nodes()) & set(eq_by_id)
    target_group_count = rng.randint(3, 8)

    while available and len(individual) < target_group_count:
        seed_id = rng.choice(tuple(available))
        target_size = rng.randint(config.group_min_size, config.group_max_size)
        group_ids = {seed_id}

        while len(group_ids) < target_size:
            candidates = {
                neighbor
                for equipment_id in group_ids
                for neighbor in graph.neighbors(equipment_id)
                if neighbor in available and neighbor not in group_ids
            }
            if not candidates:
                break
            if objective is None:
                best_candidates = list(candidates)
            else:
                current = GroupCandidate(
                    [eq_by_id[equipment_id] for equipment_id in group_ids],
                    excluded_resource_ids,
                )
                best_value = max(
                    objective.marginal(current, eq_by_id[candidate])
                    for candidate in candidates
                )
                best_candidates = [
                    candidate
                    for candidate in candidates
                    if objective.marginal(current, eq_by_id[candidate])
                    == best_value
                ]
            group_ids.add(rng.choice(best_candidates))

        available -= group_ids
        if len(group_ids) >= config.group_min_size:
            individual.append({eq_by_id[equipment_id] for equipment_id in group_ids})

    return individual


def initialize_population(
    graph: Any,
    eq_by_id: Dict[int, Equipment],
    config: ProcessingConfig,
    rng: random.Random,
    objective: Optional[GroupObjective],
    excluded_resource_ids: Set[int],
    initial_groups: Optional[List[Dict[str, Any]]] = None,
    population_size: int = 30,
) -> List[List[Set[Equipment]]]:
    """Create initial individuals from connected graph neighborhoods."""
    population = []
    for group in (initial_groups or [])[:population_size]:
        group_items = set(group.get("equipments", []))
        if group_items:
            population.append([group_items])
    for _ in range(population_size):
        if len(population) >= population_size:
            break
        population.append(
            create_graph_individual(
                graph, eq_by_id, config, rng, objective, excluded_resource_ids
            )
        )
    return population
