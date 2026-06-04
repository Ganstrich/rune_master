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
├── resource_optimizer.py     - Resource optimization (placeholder)
└── tuner.py                  - Parameter tuning engine
```

## Configuration (`config_dataclass.py`)

### `ProcessingConfig`
Dataclass controlling all pipeline behavior.

**Graph Building:**
- `graph_min_shared_ratio: float` - Jaccard similarity threshold (default: 0.2)
- `graph_min_component_size: int` - Minimum nodes per component (default: 2)

**Community Detection:**
- `algorithm: str` - `"louvain"`, `"bilouvain"`, or `"none"` (default: `"louvain"`)
- `resolution_range: tuple` - Resolution search range (default: `(1, 10, 1)`)

**Group Mapping:**
- `group_min_size: int` - Minimum equipment per group (default: 2)
- `group_max_size: int` - Maximum equipment per group (default: 18)
- `group_min_shared_resources: int` - Minimum shared resources (default: 2)
- `group_efficiency_threshold: float` - Minimum efficiency (default: 0.15)
- `use_inclusive_mapping: bool` - Broad vs strict grouping (default: False)

**Filtering:**
- `use_density_filtering: bool` - Enable density/level filter (default: True)
- `equipment_density_level_ratio: float` - Density threshold (default: 0.15)
- `fallback_to_unfiltered: bool` - Fallback if pool too small (default: True)
- `min_filtered_pool_size: int` - Minimum pool before fallback (default: 10)

**Grouping Method:**
- `grouping_method: str` - `"deterministic"`, `"random"`, `"hybrid"`, `"committee"`, `"genetic"` (default: `"deterministic"`)
- `random_group_count: int` - Groups for random method (default: 10)
- `random_seed: Optional[int]` - Reproducibility seed (default: None)

## Orchestrator (`orchestrator.py`)

### `RuneMaster`
Main entry point coordinating all grouping experts.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `run_all()` | Default pipeline (deterministic) |
| `run_deterministic()` | Pure graph-based grouping |
| `run_random_grouping()` | Stochastic group generation |
| `run_hybrid_grouping()` | Deterministic + random supplement |
| `run_committee()` | Mixture of Experts ensemble |
| `get_summary()` | Statistics dict of results |
| `print_summary()` | Pretty-print statistics |

**Mixture of Experts (MoE) Architecture:**
1. Each expert independently discovers groups
2. Gating network evaluates fitness scores
3. De-duplicates by equipment ID sets
4. Returns unified ensemble

## Graph Builder (`graph_builder.py`)

### `GraphBuilder`
Constructs equipment-resource relationship graphs.

**Pipeline:**
1. `create_bipartite_graph()` - Equipment ↔ Resource bipartite graph
2. `get_equipment_resources()` - Extract equipment → resources mapping
3. `create_jaccard_similarity_graph()` - Equipment similarity network
4. `remove_weak_candidates()` - Filter isolated/small components

**Similarity Metrics:**
- **Jaccard Index:** `shared_resources / total_unique_resources`
- **Absolute Count:** Minimum shared resources threshold
- Edge weight = max(jaccard, 0.01) to ensure non-zero for algorithms

## Community Detector (`community_detector.py`)

### `CommunityDetector`
Detects equipment communities using modularity optimization.

**Algorithms:**

| Algorithm | Method | Best For |
|-----------|--------|----------|
| Louvain | `find_best_louvain_partition()` | General-purpose, fast |
| BiLouvain | `find_best_bilouvain_partition()` | Bipartite-aware clustering |
| Connected Components | Fallback | No algorithm selection |

**Scoring Metrics:**
- `calculate_average_pairwise_similarity()` - Average Jaccard within communities
- `calculate_bulk_efficiency()` - Resource overlap efficiency

**Resolution Optimization:**
Iterates through resolution range, selects partition with highest pairwise similarity.

## Group Mapper (`group_mapper.py`)

### `GroupMapper`
Converts community partitions into enriched group dictionaries.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `calculate_shared_resources()` | Find common resources across equipment |
| `calculate_average_density()` | Mean stat weight per level |
| `calculate_total_ingredients()` | Aggregate recipe requirements |
| `create_group()` | Build full group dict with metadata |
| `map_communities()` | Standard community → group conversion |
| `map_communities_inclusive()` | Broad mapping (includes partial matches) |

**Group Dict Structure:**
```python
{
    "equipments": List[Equipment],
    "shared_resources": List[dict],
    "sharing_efficiency": float,
    "average_density": float,
    "total_ingredients": List[dict],
    "selection_method": str,
    "expert_name": str,
}
```

## Grouping Experts (`experts/`)

### Base Class (`base.py`)
Abstract `GroupingExpert` with:
- `discover_groups(equipments, config)` - Main discovery method
- `evaluate_group(group)` - Fitness scoring (override in subclasses)

### Graph Expert (`graph_expert.py`)
Uses Louvain community detection on similarity graph.
- Best for: Natural clusters with clear resource sharing
- Optimizes: Modularity and pairwise similarity

### Random Expert (`random_expert.py`)
Stochastic group generation with density filtering.
- Best for: Supplementing deterministic methods
- Features: Configurable pool filtering, duplicate avoidance

### Genetic Expert (`genetic_expert.py`)
Evolutionary optimization via selection, crossover, mutation.
- Best for: Dense graphs with complex sharing patterns
- Parameters: Population size, generations, mutation rate

## Equipment Filter (`equipment_filter.py`)

### `EquipmentFilteringStrategy`
Filters equipment pool by stat density (stat_weight / level).

**Key Methods:**
- `calculate_minimum_density(level, ratio)` - Threshold calculation
- `filter_by_density_ratio(equipments, ratio)` - Split into kept/excluded
- `get_active_pool(equipments, ...)` - Smart filtering with fallback
- `get_pool_stats(equipments)` - Pool statistics

## Stat Calculator (`stat_calculator.py`)

### Stat Weight Calculation
Formula: `weight = avg(min, max) * stat_weight[stat_type]` (only positive averages)

**Key Functions:**
- `calculate_stat_line_weight()` - Single stat line weight
- `calculate_equipment_weight()` - Total equipment weight
- `calculate_equipment_weights_batch()` - Batch processing

**STAT_WEIGHTS Mapping:**
Comprehensive table of 60+ stat names with importance weights (e.g., `PA=100`, `PM=90`, `Vitalité=0.2`).

## Parameter Tuner (`tuner.py`)

### `ParameterTuner`
Grid search for optimal grouping parameters.

**Quality Function:**
- Retention Rate: 30% weight
- Average Efficiency: 40% weight
- Group Size Sweet Spot (2-15): 30% weight
- Mega-group Penalty: -0.1 per item over 18

**Parallel Execution:**
Uses `ProcessPoolExecutor` for concurrent configuration evaluation.

## Design Principles

1. **Modular experts** - Each algorithm is independent and pluggable
2. **Configuration-driven** - Behavior controlled via `ProcessingConfig`
3. **MoE architecture** - Combine multiple strategies for best results
4. **Parallel execution** - Tuner uses multiprocessing for speed
5. **Graceful degradation** - Fallbacks at every level
