# Module: Models Module

## 1. Executive Summary & Purpose
- **Core Function:** Defines immutable dataclasses that act as the structural data containers for game equipment, resources, statistics, and crafting requirements. These classes contain no business logic or API communication.
- **Target Audience/Users:** Utilized by [data/DATA.md](file:///home/adamb/rune_master/data/DATA.md) for data instantiation and [processing/PROCESSING.md](file:///home/adamb/rune_master/processing/PROCESSING.md) for executing algorithms.
- **Design Philosophy:** Strict boundary between data definitions and business logic, default immutability to prevent accidental mutations, and type safety with automatic initialization validation.

## 2. Architectural & Structural Dependencies
- **Parent System/Universe:** RuneMaster
- **Inbound Dependencies:**
  - [data/DATA.md](file:///home/adamb/rune_master/data/DATA.md) (`loaders.py` transforms API data to these models).
  - [processing/PROCESSING.md](file:///home/adamb/rune_master/processing/PROCESSING.md) (all grouping, graph, filtering, and metric operations rely on these classes).
  - [visualization/VISUALIZATION.md](file:///home/adamb/rune_master/visualization/VISUALIZATION.md) (uses these models to display attributes in reports).
- **Outbound Dependencies:**
  - Standard library (`typing`, `dataclasses`, `enum`).
- **Interactions/Data Flow:**
  Raw JSON dictionaries from the API or cache are passed into `loaders.py` to instantiate `Resource`, `Equipment`, `EquipmentStat`, and `ResourceRequirement` objects. Once created, these models are loaded into processing pipelines, graphs, and visual templates.

### Module Files
- `models/common.py` - Shared types (ImageURLs, ItemType, StatType, StatWeight)
- `models/equipment.py` - Equipment and EquipmentStat models
- `models/resource.py` - Resource model (crafting ingredients)
- `models/recipe.py` - ResourceRequirement model (recipe entries)

## 3. Strict Rules & Mechanics (The "Hard Constraints")
| Parameter/State | Rule / Constraint | Logical Consequence |
| :--- | :--- | :--- |
| `Resource` numeric fields | Must be non-negative | Triggers validation error in `__post_init__` |
| `ResourceRequirement` `resource_id` | Must be non-negative | Triggers validation error in `__post_init__` |
| `ResourceRequirement` `quantity` | Must be positive | Triggers validation error in `__post_init__` |
| `Equipment` mutability | Not frozen (`unsafe_hash=False`) | Allows computed fields (e.g. `stat_weight`) to be set after creation |
| `Equipment` hashability | Hashed by unique `ankama_id` | Allows equipment to be used in Python sets and dictionary keys |

## 4. Key Concepts & Terminology
- **`ImageURLs`:** A TypedDict containing `icon` and `sd` URL strings.
- **`ItemType`:** A TypedDict containing `name` and `id` representing the category of the item.
- **`StatType`:** A TypedDict containing `name` and `id` representing the stat identifier.
- **`StatWeight`:** Enum mapping stat names to importance weights (e.g. `PA=100.0`, `Vitalité=0.2`).
- **`STAT_ID_TO_NAME`:** Read-only dictionary mapping stat IDs to French names.
- **`STAT_NAME_TO_ID`:** Reverse mapping of French stat names to IDs.
- **`EquipmentStat`:** Represents a single equipment effect/stat line with minimum/maximum values, ignoring flags, and formatted string.
- **`Equipment`:** Core container holding `ankama_id`, `type`, `level`, `name`, `effects` list, calculated `stat_weight`, recipe `ResourceRequirement` list, and `image_urls`.
- **`Resource`:** Represents a crafting ingredient with `ankama_id`, `name`, `description`, `type`, `level`, `pods`, and `image_urls`.

## 5. Known Gaps & Future Extensions
- **Established Backlog:**
  - Decoupling of fuzzy stat normalization from model layer (documented in [REFACTOR_PLAN.md](file:///home/adamb/rune_master/REFACTOR_PLAN.md) - Issue 3).
- **[PROPOSITION]:** None.
