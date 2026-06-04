# Models Module

Pure data containers with no business logic. All models are immutable dataclasses (except `Equipment` which allows post-init field setting for the loader layer).

## Architecture

```
models/
├── common.py       - Shared types (ImageURLs, ItemType, StatType, StatWeight)
├── equipment.py    - Equipment and EquipmentStat models
├── resource.py     - Resource model (crafting ingredients)
└── recipe.py       - ResourceRequirement model (recipe entries)
```

## Common Types (`common.py`)

| Type | Description |
|------|-------------|
| `ImageURLs` | TypedDict with `icon` and `sd` URL strings |
| `ItemType` | TypedDict with `name` and `id` for item type metadata |
| `StatType` | TypedDict with `name` and `id` for stat metadata |
| `StatWeight` | Enum mapping stat names to importance weights (e.g., `PA=100.0`, `Vitalité=0.2`) |
| `STAT_ID_TO_NAME` | Read-only mapping of stat IDs to French names |
| `STAT_NAME_TO_ID` | Reverse mapping of names to IDs |

## Equipment Model (`equipment.py`)

### `EquipmentStat`
Represents a single equipment effect/stat line with full API metadata.

**Fields:**
- `stat_type: StatType` - Stat metadata dict with `name` and `id`
- `int_minimum: int` - Minimum stat value
- `int_maximum: int` - Maximum stat value
- `ignore_int_min: bool` - Whether to display minimum
- `ignore_int_max: bool` - Whether to display maximum
- `formatted: str` - Pre-formatted display string

**Key Properties:**
- `stat_name` - Normalized stat name with fuzzy matching (handles singular/plural, case variations)
- `stat_id` - The stat's numeric ID

### `Equipment`
Core equipment data container.

**Fields:**
- `ankama_id: int` - Unique identifier (immutable, used for hashing)
- `type: ItemType` - Equipment type metadata
- `level: int` - Required level
- `name: str` - Equipment name
- `effects: List[EquipmentStat]` - Stat lines (default: empty)
- `stat_weight: Optional[float]` - Computed importance score (default: None)
- `recipe: List[ResourceRequirement]` - Crafting requirements (default: empty)
- `image_urls: Optional[ImageURLs]` - Image URLs (default: None)

**Note:** Not frozen to allow `EquipmentLoader` to set computed fields after creation.

## Resource Model (`resource.py`)

### `Resource`
Immutable dataclass representing a crafting ingredient.

**Fields:**
- `ankama_id: int` - Unique identifier
- `name: str` - Resource name
- `description: str` - Flavor text
- `type: ItemType` - Resource type metadata
- `level: int` - Resource level
- `pods: int` - Weight in pods
- `image_urls: Optional[ImageURLs]` - Image URLs (default: None)

**Validation:** All numeric fields must be non-negative.

## Recipe Model (`recipe.py`)

### `ResourceRequirement`
Immutable dataclass for a single recipe entry.

**Fields:**
- `resource_id: int` - Reference to a Resource
- `quantity: int` - Amount required (must be positive)

**Validation:** `resource_id` must be non-negative, `quantity` must be positive.

## Design Principles

1. **No business logic** - Models are pure data containers
2. **No API calls** - All external communication happens in `data/`
3. **Immutable by default** - Prevents accidental mutation
4. **Validation in `__post_init__`** - Catches invalid data early
5. **Hashable** - Equipment can be used in sets/dicts via `ankama_id`
