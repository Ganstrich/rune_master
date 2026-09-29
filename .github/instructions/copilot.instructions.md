# Copilot Instructions - Rune Master

## Project Overview

**Rune Master** is an equipment crafting optimizer for Dofus 3 that:
1. Fetches equipment data from the DofusAPI
2. Groups equipment by shared resource requirements
3. Generates static HTML reports with equipment and ingredient details
4. Runs a local web server to browse groups and visualizations

**Repository**: `/home/adamb/rune_master`
**Python Version**: 3.12+
**Entry Point**: `main.py`

### Read This First

`docs/` holds the domain model, the objective the project is actually
optimizing, an audit of known failings, and the target architecture. Start at
[docs/README.md](../../docs/README.md). Grouping exists because an item's rune
yield coefficient (`taux`) is unknowable before breaking and decays with use, so
cheap variety is the goal — not recipe overlap for its own sake.

`processing/PROCESSING.md` stays authoritative for what the code does **today**;
`docs/` describes the domain and the destination.

---

## Architecture Overview

```
main.py (orchestration)
├── data/
│   ├── api_client.py (HTTP API calls)
│   ├── cache_manager.py (persistent SQLite cache)
│   └── loaders.py (raw dicts → dataclasses)
├── models/
│   ├── equipment.py (Equipment, EquipmentStat)
│   ├── resource.py (Resource)
│   └── recipe.py (ResourceRequirement)
├── processing/
│   ├── orchestrator.py (RuneMaster main controller)
│   ├── graph_builder.py (NetworkX bipartite graphs)
│   ├── community_detector.py (Louvain community detection)
│   └── group_mapper.py (communities → groups with ingredients)
└── visualization/
    ├── html_generator.py (HTML page generation)
    └── style_templates.py (CSS/JS utilities)
```

---

## Key Implementation Details

### 1. **Data Loading Pipeline** (`data/`)

**DofusAPIClient** → Raw dicts from https://api.dofusdu.de
- `get_all_equipments()`: Fetches 259+ equipment with recipes
- `get_resource(id)`: Fetches single resource by ID

**EquipmentLoader** → Converts raw dicts to Equipment dataclasses
- Parses effects, recipes, images
- Caches results

**CacheManager** → Persistent SQLite cache (`resource_cache.db`)
- Stores equipment effects
- **CRITICAL**: Stores resource data (names, images, etc.)
- First run: fetches resources from API (~37 seconds for ~279 resources)
- Subsequent runs: instant lookup

### 2. **Processing Pipeline** (`processing/orchestrator.py`)

The **RuneMaster** orchestrator runs 4 steps:

**[1] Build Equipment Graph**
- Creates bipartite graph: equipment ↔ resources
- Filters edges by minimum shared ratio (20%)
- Output: 224 nodes, 813 edges

**[2] Detect Communities**
- Uses Louvain algorithm (modularity optimization)
- Finds ~50 communities (equipment groups)
- Tunes resolution parameter (1-10 range)

**[3] Map Communities to Groups**
- Filters by:
  - Min/max group size (2-18 equipment)
  - Min shared resources (2+)
  - Efficiency threshold (>15%)
- Calculates total ingredients per group
- **USES CACHE** for resource names

**[4] Generate Visualizations**
- Creates HTML pages for index + each group
- Each group page includes:
  - Equipment gallery (with images)
  - Ingredient table (with per-equipment breakdown)

### 3. **Resource Caching (CRITICAL)**

Located in `main.py::_cache_equipment_resources()`:

```python
# First run: fetches all ~279 resources
# Stores in cache: resource_id → {name, image_url, ...}

# Subsequent runs: cache.get_resource(id) → instant
```

**Why it matters:**
- Ingredient table shows resource **names** (e.g., "Plume du Kwak")
- Paste feature requires correct names
- Without cache: would be slow on each run
- With cache: subsequent runs take ~20 seconds (vs 50+ with fetching)

### 4. **HTML Generation** (`visualization/`)

**HTMLGenerator** produces:
- `index.html`: Shows all groups as cards with equipment lists
- `group_001.html` - `group_036.html`: Individual group pages

**Each group page layout:**
1. Header with group stats
2. Equipment gallery (thumbnail images)
3. Ingredient table (with per-equipment quantities)
4. Footer

**Important CSS classes:**
- `.ingredient-resource-name`: Resource name (used by paste feature)
- `.equipment-item`: Equipment thumbnail
- `.group-card`: Index card with equipment list

---

## Recent Improvements (Jan 16, 2026)

### ✅ Completed Tasks

1. **Equipment List on Index Cards**
   - Shows first 5 equipment names + "+X more"
   - CSS class: `.group-card-equipment-list`
   - File: `visualization/style_templates.py` (added styling)

2. **Resource Name Caching**
   - Pre-fetches all ~279 resources during load phase
   - First run: 37.53s to fetch + cache all resources
   - Subsequent runs: instant cache lookup
   - File: `main.py::_cache_equipment_resources()`

---

## Performance Metrics

| Stage | First Run | Cached Run |
|-------|-----------|-----------|
| Equipment load | 0.15s | 0.15s |
| Resource caching | 37.53s | 0s (skipped) |
| Processing | 0.5s | 0.5s |
| Visualization | 0.03s | 0.03s |
| **Total** | **~50s** | **~20s** |

---

## Common Modifications

### Add New Filter to Group Mapping
Edit `main.py::process_equipment()` → `ProcessingConfig`:
```python
config = ProcessingConfig(
    group_min_size=2,              # ← Modify here
    group_max_size=18,             # ← Modify here
    group_min_shared_resources=2,  # ← Modify here
    group_efficiency_threshold=0.15, # ← Modify here
)
```

### Change Resource Fetch Behavior
Edit `main.py::_cache_equipment_resources()`:
- Currently: fetches missing resources
- To disable: delete the function call on line ~61
- To batch differently: modify loop starting at line ~90

### Customize HTML Layout
Edit `visualization/html_generator.py::generate_group_page()`:
- Adjust the equipment gallery and ingredient table sections
- Modify `.group-card` styling in `style_templates.py`

---

## Testing & Debugging

### Run Full Pipeline
```bash
cd /home/adamb/rune_master
python3 main.py
```

Output sequence:
1. Load equipment (0.15s)
2. Cache resources (~37s on first run)
3. Run processing (0.5s)
4. Generate reports (0.03s)
5. Start server on http://127.0.0.1:8000/

### Clear Cache (Force Fresh Resource Fetch)
```bash
rm resource_cache.db resource_cache.db-wal resource_cache.db-shm
python3 main.py  # Will re-fetch all resources
```

### Check Generated Files
```bash
ls -lh visualizations/
# Should show: index.html + 35-36 group_*.html files
```

### Verify Resource Names
```bash
grep "ingredient-resource-name" visualizations/group_001.html | head -5
# Should show actual resource names, not IDs
```

---

## Key Files to Know

| File | Purpose | Last Modified |
|------|---------|---|
| `main.py` | Main orchestrator, resource caching | Jan 16 |
| `processing/orchestrator.py` | RuneMaster pipeline | Jan 16 |
| `processing/group_mapper.py` | Community → groups + ingredients | Jan 16 |
| `visualization/html_generator.py` | HTML generation | Jan 16 |
| `data/cache_manager.py` | Persistent caching | Jan 16 |
| `visualization/style_templates.py` | CSS/JS utilities | Jan 16 |

---

## Important Notes for Future Assistants

1. **Resource caching is essential** - Don't remove `_cache_equipment_resources()` function
2. **Equipment names on index** - Must show actual equipment names in group cards
3. **Paste feature needs resource names** - Without proper caching, paste won't work
4. **First run is slow** - Expected behavior (resource fetching). Document this to users.
5. **Cache location** - `resource_cache.db` (NOT in repo, gitignored)

---

## Configuration File

See `config.py` for:
- API settings (game, language, endpoints)
- Minimum/maximum equipment levels
- Item types to include
- Excluded resource IDs
- Cache file location

---

## Running RuneMaster

Make sure to use python3 and activate the venv

## Next Steps / Future Work

- [ ] Batch resource fetching (parallel requests) for faster caching
- [ ] Add resource search/filter UI
- [ ] Export groups to PDF or JSON
- [ ] Multi-language support
- [ ] Equipment similarity score visualization
- [ ] Equipment recommendation engine

---

**Last Updated**: January 16, 2026
**Project State**: Production-ready with all key features
