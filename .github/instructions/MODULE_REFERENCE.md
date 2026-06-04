# Module Reference Guide - Rune Master

For LLM assistants working on specific modules. Query this file for detailed information about a particular component.

---

## `data/api_client.py` - HTTP API Client

**Purpose**: Low-level HTTP communication with DofusAPI

**Key Methods**:
- `get_all_equipments()` → List[Dict] - Fetches all equipment with recipes
- `get_equipment(id)` → Dict - Single equipment
- `get_resource(id)` → Dict - Single resource by ID
- `get_resources_batch(ids)` → List[Dict] - Multiple resources

**Important Notes**:
- Returns raw dicts, NOT dataclasses
- Handles timeouts, connection errors gracefully
- All requests to `https://api.dofusdu.de/dofus3/v1/fr/items/...`
- No caching at this layer (that's CacheManager's job)

**Config Parameters**:
```python
BASE_URL = "https://api.dofusdu.de"
DEFAULT_TIMEOUT = 30  # seconds
```

---

## `data/cache_manager.py` - Persistent Caching

**Purpose**: SQLite-backed disk cache for expensive API calls

**Key Methods**:
- `get_resource(id)` → Dict - Raw resource dict from cache
- `set_resource(id, data)` → None - Store resource in cache
- `has_resource(id)` → bool - Check if cached
- `save()` → None - No-op (SQLite auto-commits)
- `get_stats()` → Dict - Cache size/counts

**Cache Schema**:
```sql
CREATE TABLE resources (id INTEGER PRIMARY KEY, name TEXT, data BLOB, fetched_at TEXT);
CREATE TABLE equipment_effects (equipment_id INTEGER PRIMARY KEY, effects BLOB, fetched_at TEXT);
CREATE TABLE stat_weights (equipment_id INTEGER PRIMARY KEY, weight REAL, computed_at TEXT);
```

**File Location**: `resource_cache.db` (per `config.py`)

**Important Notes**:
- Persistent across runs (not cleared automatically)
- WAL mode: safe for concurrent reads (used by tuner ProcessPoolExecutor)
- All methods are synchronous (blocking)
- To clear: `rm resource_cache.db resource_cache.db-wal resource_cache.db-shm`

---

## `data/loaders.py` - Raw Dict → Dataclass Conversion

**Key Classes**:
- `EquipmentLoader`: dict → Equipment dataclass
- `ResourceLoader`: dict → Resource dataclass

**Key Methods**:
- `from_raw_api(raw_dict)` → Equipment/Resource - Single conversion
- `from_raw_batch(list)` → List[Equipment/Resource] - Batch conversion
- `get_or_fetch(id)` → Equipment/Resource - Cache OR API

**Important Notes**:
- Pure transformation layer (no business logic)
- Validates data during conversion
- Handles KeyError/ValueError gracefully
- ResourceLoader.get_or_fetch() combines cache + API

---

## `models/` - Data Models

**equipment.py**:
- `Equipment`: Immutable dataclass with ankama_id, name, level, recipe, effects
- `EquipmentStat`: Single stat/effect with type, min/max values
- `ItemType`: TypedDict with id, name

**resource.py**:
- `Resource`: Immutable dataclass with ankama_id, name, description, type, level
- Represents crafting ingredient

**recipe.py**:
- `ResourceRequirement`: Immutable dataclass (resource_id, quantity)
- Single requirement in Equipment.recipe list

**common.py**:
- `ImageURLs`: TypedDict with various URL sizes
- `StatType`: TypedDict with id, name for equipment stats
- `ItemType`: TypedDict with id, name for item types

**Important Notes**:
- All frozen (immutable) for thread safety
- Use `@dataclass(frozen=True)` pattern
- Post-init validation in `__post_init__()`

---

## `processing/orchestrator.py` - RuneMaster Controller

**Main Class**: `RuneMaster`

**Pipeline Steps** (in `run_all()`):
1. `build_graph()` - Create bipartite graph
2. `detect_communities()` - Find equipment groups
3. `map_groups()` - Convert to filterable groups
4. `optimize_groups()` - (currently placeholder)

**Key Methods**:
- `run_all()` → List[Dict] - Full pipeline, returns groups
- `build_graph()` → (nx.Graph, Dict)
- `detect_communities()` → Dict[node_id → community_id]
- `map_groups()` → List[Dict] - Filtered groups
- `print_summary()` - Console output

**Configuration**:
```python
@dataclass
class ProcessingConfig:
    graph_min_shared_ratio: float = 0.2
    graph_min_component_size: int = 2
    algorithm: str = "louvain"  # or "bilouvain" or "none"
    resolution_range: tuple = (1, 10, 1)  # min, max, step
    group_min_size: int = 2
    group_max_size: int = 18
    group_min_shared_resources: int = 2
    group_efficiency_threshold: float = 0.15
    use_inclusive_mapping: bool = False
    excluded_resource_ids: set = None
```

**Important Notes**:
- Accepts optional `cache_manager` and `api_client`
- Stores results in instance: self.groups, self.partition, self.communities
- Does NOT save to disk

---

## `processing/graph_builder.py` - Network Graph Construction

**Key Method**: `build_equipment_graph(equipments, min_shared_ratio, min_component_size)`

**Returns**: (nx.Graph, Dict)
- Graph: Nodes = equipment + resources, Edges = recipe connections
- Dict: Resource metadata for quick lookup

**Algorithm**:
1. Create bipartite graph (equipment on left, resources on right)
2. Compute Jaccard similarity between equipment based on shared resources
3. Filter edges by minimum similarity ratio
4. Keep only connected components >= min_component_size

**Important Notes**:
- Uses NetworkX library
- Bipartite structure important for Louvain algorithm
- Returns pruned graph (removes isolated nodes)

---

## `processing/community_detector.py` - Community Detection

**Key Method**: `detect_communities_louvain(graph, resolution_range)`

**Algorithm**: Louvain modularity optimization
- Tunes resolution parameter (1-10)
- Finds optimal resolution with highest modularity
- Returns Dict[node_id → community_id]

**Alternative**: `detect_communities_bilouvain()` - Bipartite-aware version

**Important Notes**:
- Uses python-louvain library
- Modularity score higher = better separation
- Non-deterministic (randomness in algorithm)

---

## `processing/group_mapper.py` - Communities → Filterable Groups

**Main Class**: `GroupMapper`

**Key Methods**:
- `map_communities()` - Strict filtering (quality over quantity)
- `map_communities_inclusive()` - Permissive filtering (quantity over quality)
- `calculate_total_ingredients()` - **IMPORTANT: Uses cache for resource names**
- `calculate_shared_resources()- Efficiency metrics

**Ingredient Calculation**:
```python
def calculate_total_ingredients(
    group_equipments, 
    cache_manager=None,      # ← USES CACHE
    api_client=None
)
```

Process:
1. Iterate equipment recipes
2. For each resource: lookup in cache_manager
3. If found: use cached name (fast)
4. If not found: fallback to "Resource {id}"

**Group Output Format**:
```python
{
    "equipments": [Equipment, ...],
    "shared_resources_count": 15,
    "total_shared_resources": 18,
    "sharing_efficiency": 0.456,
    "total_ingredients": {
        1141: {"name": "...", "total_quantity": 12, "quantity_per_equipment": {...}},
        ...
    },
    "unique_ingredients_count": 7,
    "total_items_needed": 108,
}
```

**Important Notes**:
- MUST pass cache_manager for resource names to work
- Efficiency = shared_resources / total_unique_resources
- Filtering happens here (size, shared resources, efficiency)

---

## `visualization/html_generator.py` - HTML Page Generation

**Main Class**: `HTMLGenerator`

**Key Methods**:
- `generate_group_page(group, group_index)` → str - Full HTML
- `save_group_page(group, group_index)` → str - Save to disk
- `generate_index_page(groups)` → str - Index page
- `_build_group_cards(groups)` → str - Index cards with equipment lists
- `_build_equipment_gallery(group)` → str - Equipment thumbnails
- `_build_ingredient_table(group)` → str - Resource list table
- `_build_graph_data(group)` → Dict - D3.js data

**Page Layout** (IMPORTANT ORDER):
1. Header with stats
2. Equipment gallery
3. **Ingredient table** ← MUST BE BEFORE GRAPH
4. D3.js graph
5. Footer

**Important CSS Classes** (used by paste feature):
- `.ingredient-resource-name` - Resource name in table
- `.equipment-item-name` - Equipment name
- `.group-card-equipment-list` - Equipment list on index

**Important Notes**:
- All HTML uses pure CSS/JS (no frameworks)
- XSS-safe HTML escaping
- Responsive design (mobile-friendly)

---

## `visualization/graph_generator.py` - D3.js Graph

**Key Function**: `create_graph_html(graph_data)`

**Input Graph Data**:
```python
{
    "nodes": [
        {"id": "equip_123", "name": "Equipment Name", "type": "equipment", ...},
        {"id": "res_456", "name": "Resource Name", "type": "resource", ...},
    ],
    "links": [
        {"source": "equip_123", "target": "res_456", "quantity": 5},
    ]
}
```

**D3.js Features**:
- Force-directed simulation
- Drag-to-move nodes
- Scroll-to-zoom
- Hover tooltips
- Legend (blue = equipment, green = resources)
- Responsive resizing

**Important Notes**:
- Embeds entire D3.js library (v7.min.js via CDN)
- Graph data embedded as JSON in HTML
- JavaScript initializes on `DOMContentLoaded`

---

## `visualization/style_templates.py` - CSS/JS Utilities

**Key Functions**:
- `get_base_css()` - Common styles (reset, theming, typography)
- `get_group_css()` - Group page styles
- `get_index_css()` - Index page styles
- `get_graph_javascript()` - D3.js initialization code
- `get_javascript_utils()` - Utility functions (copy, search, sort)

**CSS Variables** (theming):
```css
--color-primary: #4f46e5
--color-accent: #7c3aed
--color-success: #10b981
--color-gray-*: Various shades
--spacing-*: Padding/margin sizes
```

**Important Notes**:
- All CSS scoped with specific classes
- No Bootstrap or Tailwind (pure CSS)
- Accessibility-first (WCAG 2.1 AA)

---

## `main.py` - Main Orchestration

**Entry Point**: `main()`

**Pipeline**:
1. `load_equipment()` - Fetch + cache resources
2. `process_equipment()` - RuneMaster pipeline
3. `generate_visualizations()` - HTML generation
4. `start_server()` - HTTP server

**Key Function**: `_cache_equipment_resources(equipments, cache, api)`

This is CRITICAL:
- Extracts all resource IDs from equipment recipes
- Fetches missing resources from API (first run only)
- Stores in cache for future runs
- Progress: "⏳ Cached 20/279 resources..."
- Time: ~37 seconds on first run (one-time)

**Important Notes**:
- `load_equipment()` returns: (equipments, cache, api)
- Resources cached before processing starts
- Server starts on http://127.0.0.1:8000/
- Serves from `visualizations/` directory

---

## `config.py` - Configuration

**Key Settings**:
```python
CACHE_FILE = "resource_cache.db"
GAME = "dofus3"
LANGUAGE = "fr"  # French
ITEM_TYPES = [list of equipment types]
MIN_LEVEL = 1
MAX_LEVEL = 230
EXCLUDED_RESOURCES = [list of resource IDs to exclude]
```

**Important Notes**:
- Modify here for different languages/regions
- Excluded resources won't count toward efficiency

---

## Debugging Checklist

**Resources not showing real names?**
- [ ] Check cache file exists: `ls ~/.cache/rune_master_cache.json`
- [ ] Cache manager passed to RuneMaster? (check main.py line ~98)
- [ ] Resource lookup failing silently? (add prints to group_mapper.py)

**Server not working?**
- [ ] Server starting in visualizations dir? (check main.py start_server)
- [ ] Check port 8000 not in use: `lsof -i :8000`
- [ ] HTML files generated? `ls visualizations/`

**Groups not generating?**
- [ ] Check filters in ProcessingConfig (too strict?)
- [ ] Verify graph has edges (check graph_builder output)
- [ ] Check community detection found communities

**D3.js graph not rendering?**
- [ ] Open browser console for errors
- [ ] Check graph-data element in HTML: `grep graph-data group_001.html`
- [ ] Verify D3.js loads: `grep d3.v7 group_001.html`

---

**Last Updated**: January 16, 2026
**Reference Version**: Current production build
