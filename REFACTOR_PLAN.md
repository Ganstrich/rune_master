# Module: Refactor Plan: Processing Module Improvements

## 1. Executive Summary & Purpose
- **Core Function:** Defines a step-by-step refactoring strategy to resolve three architectural issues in the processing layers: duplicated metrics logic, dual configuration syncing overhead, and circular imports.
- **Target Audience/Users:** Developers and AI architects modifying the system architecture.
- **Design Philosophy:** Modularity, single source of truth, and strict hierarchy (separating data representations from processing logic).

## 2. Architectural & Structural Dependencies
- **Parent System/Universe:** RuneMaster
- **Inbound Dependencies:** None (architecture plan).
- **Outbound Dependencies:**
  - [models/MODELS.md](file:///home/adamb/rune_master/models/MODELS.md) (removes circular weight import).
  - [processing/PROCESSING.md](file:///home/adamb/rune_master/processing/PROCESSING.md) (extracts `GroupMetrics` and updates config defaults).
  - [data/DATA.md](file:///home/adamb/rune_master/data/DATA.md) (changes loader dependency from global config to dataclass config).
- **Interactions/Data Flow:**
  Outlines parameters and data flow cleanup. Replaces inline and copy-pasted metric functions in `GroupMapper` and `RandomGroupBuilder` with delegation to a new `GroupMetrics` class.

## 3. Strict Rules & Mechanics (The "Hard Constraints")
| Parameter/State | Rule / Constraint | Logical Consequence |
| :--- | :--- | :--- |
| Model Imports | `models/` must not import from `processing/` | Eliminates circular import risk between models and stat calculators |
| Group Schema | Output dictionary structure must remain identical | Prevents breaking visualizer templates |
| Configuration | `ProcessingConfig` becomes single source of truth for processing | Eliminates manually copying attributes from `Config` |
| API Configuration | Settings like `MIN_LEVEL` must remain in `config.py` | Keeps data access separate from processing parameters |

## 4. Key Concepts & Terminology
- **Circular Dependency:** A situation where two or more modules depend on each other directly or indirectly, causing import errors.
- **`GroupMetrics`:** Proposed helper module containing static, pure math functions to calculate efficiency, overlaps, densities, and build the canonical group dict.
- **`resolve_stat_name`:** Proposed calculator helper mapping raw API names to internal weights.

## 5. Known Gaps & Future Extensions
- **Established Backlog:**
  - Execute steps: Issue 3 first (break dependency), Issue 1 second (extract metrics), Issue 2 last (consolidate config).
  - Validate with pytest: `python -m pytest test/test_group_structure.py` and run pipelines.
- **[PROPOSITION]:** None.
