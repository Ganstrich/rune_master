# Data Module

Handles all external communication, caching, and data transformation. Bridges the gap between raw API responses and clean dataclasses.

## Architecture

```
data/
├── api_client.py    - Low-level HTTP client for DofusAPI
├── cache_manager.py - Persistent disk-based JSON caching
└── loaders.py       - Transform raw API dicts → dataclasses
```

## API Client (`api_client.py`)

### `DofusAPIClient`
Low-level HTTP client for the Dofus API (`api.dofusdu.de`).

**Responsibilities:**
- HTTP requests with timeout and error handling
- Raw JSON response management
- NO caching or dataclass conversion

**Key Methods:**

| Method | Description |
|--------|-------------|
| `get_all_equipments()` | Fetch all craftable equipment with recipes |
| `get_equipment(id)` | Fetch single equipment by ID |
| `get_resource(id)` | Fetch single resource by ID |
| `get_resources_batch(ids)` | Fetch multiple resources (individual calls) |

**Configuration:**
- `game: str` - Game identifier (default: `'dofus3'`)
- `language: str` - Language code (default: `'fr'`)
- `timeout: int` - Request timeout in seconds (default: 30)

## Cache Manager (`cache_manager.py`)

### `CacheManager`
Persistent disk-based cache using JSON file storage.

**Cache Structure:**
```json
{
  "resources": { "123": {...raw data...} },
  "equipment_effects": { "456": [{...effect...}] },
  "stat_weights": { "789": 45.5 },
  "metadata": { "version": "1" }
}
```

**Key Methods:**

| Category | Methods |
|----------|---------|
| **Resources** | `get_resource()`, `set_resource()`, `has_resource()`, `get_resource_name()` |
| **Effects** | `get_equipment_effects()`, `set_equipment_effects()`, `has_equipment_effects()` |
| **Weights** | `get_stat_weight()`, `set_stat_weight()`, `has_stat_weight()` |
| **Utility** | `save()`, `clear()`, `get_stats()` |

**Features:**
- Automatic corruption recovery
- Safe for concurrent reads
- Statistics for monitoring cache hit rates

## Loaders (`loaders.py`)

### `EquipmentLoader`
Transforms raw equipment API responses into `Equipment` dataclasses.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `from_raw_api(raw)` | Convert single raw dict → Equipment |
| `from_raw_batch(raw_list)` | Convert multiple dicts, skip invalid |
| `compute_stat_weight(eq)` | Calculate importance score from effects |
| `get_effects_cached(id)` | Get effects from cache or API |

**Processing Pipeline:**
1. Parse basic fields (ID, type, name, level)
2. Parse effects into `EquipmentStat` objects
3. Parse recipe into `ResourceRequirement` objects
4. Compute and cache stat weight
5. Filter by minimum density if configured

### `ResourceLoader`
Transforms raw resource API responses into `Resource` dataclasses.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `from_raw_api(raw)` | Convert single raw dict → Resource |
| `from_raw_batch(raw_list)` | Convert multiple dicts, skip invalid |
| `get_or_fetch(id)` | Get from cache or fetch from API |

**Features:**
- Automatic caching on load
- Graceful error handling with skip-and-continue

## Design Principles

1. **Separation of concerns** - API, caching, and transformation are separate
2. **Cache-first** - Always check cache before making API calls
3. **Fail gracefully** - Skip invalid entries, continue processing
4. **No business logic** - Loaders only transform data, don't make decisions
5. **Type safety** - Full type hints on all public methods
