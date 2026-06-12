# Module: RuneMaster Orchestrator

## 1. Executive Summary & Purpose
- **Core Function:** A production-ready pipeline for discovering optimal equipment groups in Dofus using community detection (Louvain/BiLouvain), genetic algorithms, and a Mixture of Experts (MoE) architecture, generating interactive D3.js visual reports.
- **Target Audience/Users:** Game developers, players, or data scientists looking to optimize crafting recipes and item grouping.
- **Design Philosophy:** Performance-oriented (utilizes disk caching), algorithmically flexible (multiple expert algorithms), and visually interactive.

### Quick Start
```bash
# Install dependencies
pip install networkx python-louvain numpy requests

# Run the complete pipeline
python3 main.py

# Options
python3 main.py --grouping-method committee    # Use all experts
python3 main.py --tune                         # Auto-tune parameters
python3 main.py --no-serve                     # Generate without server
```

## 2. Architectural & Structural Dependencies
- **Parent System/Universe:** RuneMaster System
- **Inbound Dependencies:**
  - CLI Users / Orchestrator Agents
- **Outbound Dependencies:**
  - [models/MODELS.md](file:///home/adamb/rune_master/models/MODELS.md) - Pure dataclasses representing game entities.
  - [data/DATA.md](file:///home/adamb/rune_master/data/DATA.md) - API client, JSON/SQLite cache, and loaders.
  - [processing/PROCESSING.md](file:///home/adamb/rune_master/processing/PROCESSING.md) - Graph construction and grouping experts.
  - [visualization/VISUALIZATION.md](file:///home/adamb/rune_master/visualization/VISUALIZATION.md) - HTML/D3.js report generators.
  - [serve.py](file:///home/adamb/rune_master/serve.py) - HTTP serving utilities.
- **Interactions/Data Flow:**
  CLI parameters are parsed in [main.py](file:///home/adamb/rune_master/main.py). The data module loads API equipment, caches it, passes it to processing experts, maps them to communities/groups, and sends them to visualization generators to output interactive pages.

### Project Directory Structure
```
rune_master/
├── models/              # Data layer (MODELS.md)
│   ├── common.py        # Shared types, enums, stat mappings
│   ├── equipment.py     # Equipment, EquipmentStat
│   ├── resource.py      # Resource (crafting ingredients)
│   └── recipe.py        # ResourceRequirement
├── data/                # Data access layer (DATA.md)
│   ├── api_client.py    # DofusAPI HTTP client
│   ├── cache_manager.py # JSON disk cache
│   └── loaders.py       # API → dataclass transformation
├── processing/          # Business logic (PROCESSING.md)
│   ├── experts/         # Grouping algorithms
│   │   ├── base.py      # Abstract GroupingExpert
│   │   ├── graph_expert.py
│   │   ├── random_expert.py
│   │   └── genetic_expert.py
│   ├── orchestrator.py  # RuneMaster main coordinator
│   ├── graph_builder.py # Bipartite & similarity graphs
│   ├── community_detector.py  # Louvain/BiLouvain
│   ├── group_mapper.py  # Community → group conversion
│   ├── equipment_filter.py    # Density filtering
│   ├── stat_calculator.py     # Equipment scoring
│   ├── tuner.py         # Parameter optimization
│   └── config_dataclass.py    # ProcessingConfig
├── visualization/       # Report generation (VISUALIZATION.md)
│   ├── html_generator.py      # HTML page generation
│   ├── style_templates.py     # CSS/JS templates
│   └── graph_generator.py     # D3.js graphs
├── config.py            # Global configuration
├── main.py              # CLI entry point
└── serve.py             # HTTP server
```

## 3. Strict Rules & Mechanics (The "Hard Constraints")
| Parameter/State | Rule / Constraint | Logical Consequence |
| :--- | :--- | :--- |
| CLI `--grouping-method` | Must choose from: `deterministic`, `random`, `hybrid`, `committee`, `genetic` | Invalid choice raises parser validation error |
| Execution Environment | Python 3.6+ required | Dependency libraries may not run or import correctly on older versions |
| CLI `--random-groups` | Expects integer N | Number of random groups generated |
| CLI `--density-ratio` | Expects float R | Modifies density/level filtering ratio |
| CLI `--tune` | Triggers parallel parameter search | Executes grid-search optimization of parameters |

## 4. Key Concepts & Terminology
- **Committee Method:** Ensemble Mixture of Experts (MoE) grouping method combining deterministic, random, genetic, and hybrid experts.
- **Deterministic Method:** Louvain community detection on a similarity graph of equipment.
- **Genetic Method:** Evolutionary algorithm optimizing equipment groups on dense/complex graphs.
- **Hybrid Method:** Combines deterministic clustering with random supplementation for balanced coverage.
- **Random Method:** Stochastic group selection with density filtering.

## 5. Known Gaps & Future Extensions
- **Established Backlog:**
  - SQLite database migration plan ([REFACTOR_PLAN_CACHE.md](file:///home/adamb/rune_master/REFACTOR_PLAN_CACHE.md)).
  - Separation of CSS/JS, heatmaps, and side-by-side comparison ([VISUALIZATION_ROADMAP.md](file:///home/adamb/rune_master/VISUALIZATION_ROADMAP.md)).
  - Processing module metrics and dependency cleanup ([REFACTOR_PLAN.md](file:///home/adamb/rune_master/REFACTOR_PLAN.md)).
- **[PROPOSITION]:** None.
