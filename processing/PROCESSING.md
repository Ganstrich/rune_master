# Processing Module

Core business logic for equipment group discovery using graph algorithms, community detection, and a Mixture of Experts (MoE) architecture.

## Architecture

```
processing/
├── experts/                  - Specialized grouping algorithms
│   ├── base.py               - Abstract GroupingExpert base class
│   ├── graph_expert.py       - Louvain community detection
│   ├── random_expert.py      - Stochastic group generation
│   └── genetic_expert.py     - Evolutionary optimization
├── config_dataclass.py       - ProcessingConfig configuration
├── orchestrator.py           - RuneMaster main orchestrator
├── graph_builder.py          - Bipartite & similarity graph construction
├── community_detector.py     - Louvain/BiLouvain community detection
├── group_mapper.py           - Community → group conversion
├── equipment_filter.py       - Density/level ratio filtering
├── random_group_builder.py   - Random group generation
├── stat_calculator.py        - Equipment stat weight calculation
└── tuner.py                  - Parameter tuning engine
```

## Configuration (`config_dataclass.py`)

### `ProcessingConfig`
Dataclass controlling all pipeline behavior.

**Graph Building:**
- `graph_min_shared_ratio: float` - Jaccard similarity threshold (default: `0.3`)
- `graph_min_component_size: int` - Minimum nodes per component (default: `2`)

**Community Detection:**
- `algorithm: str` - `"louvain"`, `"bilouvain"`, or `"none"` (default: `"louvain"`)
- `resolution_range: tuple` - Resolution search range (default: `(1, 10, 1)`)

**Group Mapping:**
- `group_min_size: int` - Minimum equipment per group (default: `2`)
- `group_max_size: int` - Maximum equipment per group (default: `18`)
- `group_min_shared_resources: int` - Minimum shared resources (default: `3`)
- `group_efficiency_threshold: float` - Minimum efficiency (default: `0.15`)
- `use_inclusive_mapping: bool` - Broad vs strict grouping (default: `False`)

**Resource Exclusions:**
- `excluded_resource_ids: set` - Resource IDs excluded from sharing efficiency (default: `{15263, 14635}`)

**Filtering:**
- `use_density_filtering: bool` - Enable density/level filter (default: `True`)
- `equipment_density_level_ratio: float` - Density threshold (default: `0.15`)
- `fallback_to_unfiltered: bool` - Fallback if pool too small (default: `True`)
- `min_filtered_pool_size: int` - Minimum pool before fallback (default: `10`)
- `min_sharing_percentage: int` - Minimum sharing percentage (default: `60`)

**Grouping Method:**
- `grouping_method: str` - `"deterministic"`, `"random"`, `"hybrid"`, `"committee"`, `"genetic"` (default: `"hybrid"`)
- `random_group_count: int` - Groups for random method (default: `50`)
- `random_seed: Optional[int]` - Reproducibility seed (default: `None`)

**Equipment Pre-filtering:**
- `min_equipment_density: float` - Minimum stat_weight per level (default: `0.0`, disabled)

## Orchestrator (`orchestrator.py`)

### `RuneMaster`
Main entry point coordinating all grouping experts.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `run_all()` | Runs deterministic pipeline (backward compatibility) |
| `run_deterministic()` | Pure graph-based grouping |
| `run_random_grouping()` | Stochastic group generation |
| `run_hybrid_grouping()` | Deterministic + random supplement |
| `run_committee()` | Mixture of Experts ensemble |
| `get_summary()` | Statistics dict of results |
| `print_summary()` | Pretty-print statistics |

**Mixture of Experts (MoE) Architecture:**
1. Each expert independently discovers groups
2. Gating network evaluates fitness scores via `evaluate_group()`
3. De-duplicates by equipment ID sets (sorted ankama_id lists)
4. Returns unified ensemble sorted by fitness (descending)

**Summary Statistics:**
```python
{
    "total_groups": int,
    "total_equipment_in_groups": int,
    "total_equipment": int,
    "retention_rate": float,        # equipment in groups / total
    "average_efficiency": float,    # mean sharing_efficiency
    "max_efficiency": float,
    "min_efficiency": float,
    "average_group_size": float,
    "max_group_size": int,
}
```

## Graph Builder (`graph_builder.py`)

### `GraphBuilder`
Constructs equipment-resource relationship graphs. All methods are static.

**Main Pipeline:**
- `build_equipment_graph(equipments, min_shared_ratio, min_shared_count, min_component_size)` → `(graph, equipment_resources)`
  1. `create_bipartite_graph()` - Equipment ↔ Resource bipartite graph
  2. `get_equipment_resources()` - Extract equipment → resources mapping
  3. `create_jaccard_similarity_graph()` - Equipment similarity network
  4. `remove_weak_candidates()` - Filter isolated/small components

**Similarity Metrics:**
- **Jaccard Index:** `shared_resources / total_unique_resources`
- **Absolute Count:** Minimum shared resources threshold (`min_shared_count`)
- Edge weight = `max(jaccard, 0.01)` to ensure non-zero for algorithms
- Edge also stores `shared_count` attribute

## Community Detector (`community_detector.py`)

### `CommunityDetector`
Detects equipment communities using modularity optimization. All methods are static.

**Algorithms:**

| Algorithm | Method | Best For |
|-----------|--------|----------|
| Louvain | `find_best_louvain_partition()` | General-purpose, fast |
| BiLouvain | `find_best_bilouvain_partition()` | Bipartite-aware clustering |
| Connected Components | Fallback in GraphExpert | No algorithm selection |

**Utility Methods:**
- `partition_to_communities(partition)` - Converts `{node: community_id}` → `{community_id: [nodes]}`

**Scoring Metrics:**
- `calculate_average_pairwise_similarity()` - Average Jaccard within communities
- `calculate_bulk_efficiency()` - Resource overlap efficiency

**Resolution Optimization:**
Iterates through resolution range (using `np.arange`), selects partition with highest pairwise similarity.

## Group Mapper (`group_mapper.py`)

### `GroupMapper`
Converts community partitions into enriched group dictionaries.

**Constructor:**
```python
GroupMapper(equipments: List[Equipment], excluded_resource_ids: Optional[set] = None)
```

**Key Methods:**

| Method | Description |
|--------|-------------|
| `calculate_shared_resources()` | Returns `(shared_count, total_shared_count, efficiency)` |
| `calculate_average_density()` | Mean stat_weight per equipment |
| `calculate_total_ingredients()` | Aggregate recipe requirements with resource names |
| `create_group()` | Build full group dict with metadata |
| `map_communities()` | Standard community → group conversion |
| `map_communities_inclusive()` | Broad mapping with group splitting |

**Group Dict Structure:**
```python
{
    "equipments": List[Equipment],
    "shared_resources_count": int,        # Resources shared by 2+ (excl. excluded)
    "total_shared_resources": int,        # Resources shared by 2+ (incl. excluded)
    "sharing_efficiency": float,          # shared / total_unique
    "average_density": float,             # Mean stat_weight
    "total_ingredients": Dict[int, dict], # resource_id -> {name, total_quantity, ...}
    "unique_ingredients_count": int,
    "total_items_needed": int,
    "group_size": int,
    "selection_method": str,              # Set by experts
    "expert_name": str,                   # Set by experts
}
```

## Grouping Experts (`experts/`)

### Base Class (`base.py`)
Abstract `GroupingExpert` with:
- `__init__(name, cache_manager, api_client)` - Constructor
- `discover_groups(equipments, config)` - Abstract main discovery method
- `evaluate_group(group)` - Fitness scoring (default: `sharing_efficiency`)

### Graph Expert (`graph_expert.py`)
Uses Louvain community detection on similarity graph.
- Name: `"GraphExpert"`
- Best for: Natural clusters with clear resource sharing
- Optimizes: Modularity and pairwise similarity
- Pipeline: GraphBuilder → CommunityDetector → GroupMapper

### Random Expert (`random_expert.py`)
Stochastic group generation with density filtering.
- Name: `"RandomExpert"`
- Best for: Supplementing deterministic methods
- Features: Configurable pool filtering, duplicate seed avoidance
- Uses `EquipmentFilteringStrategy` and `RandomGroupBuilder`

### Genetic Expert (`genetic_expert.py`)
Evolutionary optimization via selection, crossover, mutation.
- Name: `"GeneticExpert"`
- Best for: Dense graphs with complex sharing patterns
- Parameters: `population_size=30`, `generations=50`, `mutation_rate=0.3`, `elite_count=3`
- Uses graph-aware seeding for initial population
- Fitness: sharing_efficiency with size constraints

## Random Group Builder (`random_group_builder.py`)

### `RandomGroupBuilder`
Builds equipment groups by random selection and resource matching. Standalone class used by `RandomGroupingExpert`.

**Process:**
1. Randomly select a seed equipment
2. Find companion equipment sharing resources with seed
3. Return group with metadata about selection method

**Key Methods:**
- `select_random_seed(equipment_pool, used_seeds)` - Random seed selection
- `find_companions(seed_equipment, equipment_pool, min_shared_resources)` - Find similar equipment
- `build_random_group(equipment_pool, ...)` - Build single group
- `build_multiple_random_groups(equipment_pool, count, ...)` - Build multiple groups

## Equipment Filter (`equipment_filter.py`)

### `EquipmentFilteringStrategy`
Filters equipment pool by stat density (stat_weight / level). All methods are static.

**Key Methods:**
- `calculate_minimum_density(level, ratio)` - Threshold calculation
- `filter_by_density_ratio(equipments, ratio)` - Split into kept/excluded
- `get_active_pool(equipments, ...)` - Smart filtering with fallback
- `get_pool_stats(equipments)` - Pool statistics

## Stat Calculator (`stat_calculator.py`)

### Stat Weight Calculation
Formula: `weight = avg(min, max) * stat_weight[stat_type]` (only positive averages)

**Key Functions:**
- `calculate_stat_line_weight(stat_type, min_value, max_value, stat_weights)` - Single stat line
- `calculate_equipment_weight(equipment, stat_weights)` - Total equipment weight
- `calculate_equipment_weights_batch(equipments, stat_weights)` - Batch processing
- `validate_stat_weights(stat_weights)` - Validation utility
- `get_stat_weights_summary(stat_weights)` - Human-readable summary

**STAT_WEIGHTS Mapping:**
~50 stat names with importance weights (e.g., `PA=100`, `PM=90`, `Vitalité=0.2`). Includes singular/plural variants for resilient matching (e.g., `"Dommage"` and `"Dommages"` both map to `5`).

## Parameter Tuner (`tuner.py`)

### `ParameterTuner`
Grid search for optimal grouping parameters.

**Quality Function (`evaluate_quality`):**
- Retention Rate: 30% weight
- Average Efficiency: 40% weight
- Group Size Sweet Spot (2-15): 30% weight
  - 2-15 items: score 1.0
  - 15-18 items: score 0.5
  - Otherwise: score 0.0
- Mega-group Penalty: `-0.1` per item over 18 (applied to max_group_size)

**Search Space:**
- Ratios: `[0.15, 0.2, 0.25, 0.3]`
- Min shared counts: `[2, 3, 4]`
- Methods: `"deterministic"`, `"random"`, `"committee"`, `"genetic"`

**Parallel Execution:**
Uses `ProcessPoolExecutor` for concurrent configuration evaluation. Worker uses relaxed `equipment_density_level_ratio=1.5` for tuning.

**Standalone Worker:**
`_worker_run_config()` runs in separate process with its own `CacheManager` instance.

## Design Principles

1. **Modular experts** - Each algorithm is independent and pluggable
2. **Configuration-driven** - Behavior controlled via `ProcessingConfig`
3. **MoE architecture** - Combine multiple strategies for best results
4. **Parallel execution** - Tuner uses multiprocessing for speed
5. **Graceful degradation** - Fallbacks at every level
