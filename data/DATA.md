# Module: Data Module

## 1. Executive Summary & Purpose
- **Core Function:** Handles all external communications with the Dofus API, manages persistent disk-based caching, and converts raw JSON responses into typed models.
- **Target Audience/Users:** Invoked by orchestrators like [main.py](file:///home/adamb/rune_master/main.py) and processing experts to retrieve and filter equipment/resource data.
- **Design Philosophy:** Separation of concerns (separate API access, cache storage, and data loaders), caching-first approach (checks disk storage before hitting networks), and graceful failure (skips individual invalid API items instead of crashing).

## 2. Architectural & Structural Dependencies
- **Parent System/Universe:** RuneMaster
- **Inbound Dependencies:**
  - [main.py](file:///home/adamb/rune_master/main.py) (instantiates cache and loader to run the execution pipeline).
  - [processing/PROCESSING.md](file:///home/adamb/rune_master/processing/PROCESSING.md) (uses cache manager for stats and loads equipment pools).
- **Outbound Dependencies:**
  - [models/MODELS.md](file:///home/adamb/rune_master/models/MODELS.md) (loaders map raw data to these dataclasses).
  - Dofus API (`api.dofusdu.de`).
- **Interactions/Data Flow:**
  API Client (`api_client.py`) fetches raw JSON -> Cache Manager (`cache_manager.py`) stores or reads cached responses -> Loaders (`loaders.py`) compile JSON into dataclasses -> Returns models to processing/orchestration.

### Module Files
- `data/api_client.py` - Low-level HTTP client for DofusAPI
- `data/cache_manager.py` - Disk-based caching
- `data/loaders.py` - Dataclass instantiation and computed weights

## 3. Strict Rules & Mechanics (The "Hard Constraints")
| Parameter/State | Rule / Constraint | Logical Consequence |
| :--- | :--- | :--- |
| API Communication | Client does not perform caching or conversion | Returns pure raw JSON, keeping network operations decoupled |
| Cache File Access | Concurrent writes are not safe (for original JSON caching) | Risk of file corruption or truncation if written in parallel (e.g. during auto-tuning) |
| Loader Conversion | Skip invalid API dictionaries | Skips faulty data entries and logs/continues instead of throwing an exception |
| Stat Weight Calculation | Computed and cached on load | Equipment density filters depend on the loader compiling stat weights during ingestion |

## 4. Key Concepts & Terminology
- **`DofusAPIClient`:** High-level wrapper for HTTP calls to the Dofus API (`api.dofusdu.de`) with configurable defaults for game (e.g. `'dofus3'`), language (e.g. `'fr'`), and timeout (default: `30` seconds).
- **`CacheManager`:** Storage interface managing cached resources, equipment stats, and weights.
- **`EquipmentLoader`:** Builder that constructs `Equipment` dataclasses, parses API effects/recipes, and computes initial density scores.
- **`ResourceLoader`:** Builder that constructs `Resource` dataclasses and manages batch fetching fallback logic.

## 5. Known Gaps & Future Extensions
- **Established Backlog:**
  - SQLite Database cache backend migration plan ([REFACTOR_PLAN_CACHE.md](file:///home/adamb/rune_master/REFACTOR_PLAN_CACHE.md)) to support concurrency-safe WAL-mode.
  - Consolidate config defaults in loaders ([REFACTOR_PLAN.md](file:///home/adamb/rune_master/REFACTOR_PLAN.md) - Issue 2).
- **[PROPOSITION]:** None.
