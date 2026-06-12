# Module: Processing Module

## 1. Executive Summary & Purpose
- **Core Function:** Contains the core business logic for finding optimal groups of equipment. It builds relationship graphs between equipment items based on shared crafting resources, detects communities via modularity/evolutionary algorithms, and ensembles them using a Mixture of Experts (MoE) architecture.
- **Target Audience/Users:** Executed by [main.py](file:///home/adamb/rune_master/main.py) and parameters tuned by the grid-search parameter tuner engine.
- **Design Philosophy:** Modularity (experts are pluggable and independent), configuration-driven constraints, parallel optimization, and fallback stability.

## 2. Architectural & Structural Dependencies
- **Parent System/Universe:** RuneMaster
- **Inbound Dependencies:**
  - [main.py](file:///home/adamb/rune_master/main.py) (instantiates and configures the orchestrator).
  - [visualization/VISUALIZATION.md](file:///home/adamb/rune_master/visualization/VISUALIZATION.md) (renders generated groups and recipes).
- **Outbound Dependencies:**
  - [models/MODELS.md](file:///home/adamb/rune_master/models/MODELS.md) (uses data objects).
  - [data/DATA.md](file:///home/adamb/rune_master/data/DATA.md) (reads cached resources and weight records).
- **Interactions/Data Flow:**
  Receives loaded lists of `Equipment` -> Filters them by density (`equipment_filter.py`) -> Passes them to grouping experts (Louvain, genetic, random, hybrid) -> Ensembles results via the `RuneMaster` orchestrator gating network -> Outputs enriched groups to visualization.

### Module Files
- `processing/experts/` - Folder containing specialized grouping expert classes (base, graph, random, genetic)
- `processing/config_dataclass.py` - Configuration parameters
- `processing/orchestrator.py` - RuneMaster main orchestrator coordinator
- `processing/graph_builder.py` - Bipartite and similarity network builder
- `processing/community_detector.py` - Louvain/BiLouvain community finder
- `processing/group_mapper.py` - Maps discovered communities back to enriched group dicts
- `processing/equipment_filter.py` - Density/level filtering logic
- `processing/random_group_builder.py` - Helper generating random groups
- `processing/stat_calculator.py` - Scoring functions and weight mappings
- `processing/tuner.py` - Multiprocessing parameter optimizer

## 3. Strict Rules & Mechanics (The "Hard Constraints")
| Parameter/State | Rule / Constraint | Logical Consequence |
| :--- | :--- | :--- |
| Similarity Graph Edge | Jaccard ratio >= `graph_min_shared_ratio` AND absolute shared count >= `graph_min_shared_count` | Edges not satisfying BOTH conditions are discarded |
| Graph Edge Weight | Must be non-zero | Initialized as `max(jaccard, 0.01)` |
| Component Size | Sub-components must be >= `graph_min_component_size` | Isolated/small components are removed |
| Group Size limits | Size must be >= `group_min_size` AND <= `group_max_size` (default 18) | Groups falling outside limits are discarded or split |
| Sharing Efficiency | Excludes items in `excluded_resource_ids` | Common ingredients are excluded from skewing similarity |
| Pool Filtering | Active pool size < `min_filtered_pool_size` | Falls back to unfiltered equipment pool |
| Tuner Evaluation | Group sizes over 18 | Applies a penalty of `-0.1` per equipment over 18 |

## 4. Key Concepts & Terminology
- **Jaccard similarity:** The ratio of shared recipe resource IDs to total unique recipe resource IDs of two items.
- **RuneMaster Orchestrator:** The primary coordinator coordinating grouping methods.
- **Mixture of Experts (MoE):** Ensemble setup combining independent experts and picking unique groups sorted by fitness.
- **Gating Network:** De-duplicates overlapping equipment ID sets across experts.
- **Community Detection:** High-modularity partition detection via Louvain (general Jaccard graph) or BiLouvain (bipartite graphs).
- **Stat Density:** The computed `stat_weight / level` representing item value.
- **Genetic Expert:** Evolutionary solver using selection, crossover, and mutations on graph-aware seeds.

## 5. Known Gaps & Future Extensions
- **Established Backlog:**
  - `resource_optimizer.py` is a placeholder (not fully implemented).
  - Metrics duplication and model-dependency issues resolved in [REFACTOR_PLAN.md](file:///home/adamb/rune_master/REFACTOR_PLAN.md).
- **[PROPOSITION]:** None.
