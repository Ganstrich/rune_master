# Rune Master - Copilot Instructions

## Project Overview
Rune Master is a Dofus 3 equipment crafting optimizer that:
1. Fetches equipment and resource data from the Dofus API
2. Builds bipartite graphs connecting equipment to their recipe resources
3. Identifies equipment groups with shared resources for bulk crafting
4. Generates interactive HTML visualizations of resource networks

## Tech Stack
- **Backend**: Python 3 (Flask optional for web UI)
- **Data Processing**: NetworkX, Pandas, NumPy
- **Graph Algorithms**: Community detection (Louvain, BiLouvain), Jaccard similarity
- **Visualization**: D3.js (frontend), Plotly (analysis), custom HTML/CSS
- **API**: Dofus API (dofusdu.de)
- **Caching**: JSON file-based resource cache

## Core Architecture

### Data Flow
1. `DofusAPI` → Fetch equipment with recipes from API
2. `DataProcessor` → Build graphs, detect communities, calculate efficiency metrics
3. `EquipmentVisualizer` → Generate interactive HTML reports
4. Browser → View D3.js force-directed graphs + ingredient tables

### Key Classes
- **Equipment**: Dataclass with ankama_id, level, name, recipe (List[ResourceRequirement])
- **Resource**: Cached resource metadata (id, name, level, rarity, image_urls)
- **DataProcessor**: Graph algorithms (Jaccard similarity, Louvain partitioning, greedy exploration)
- **EquipmentVisualizer**: HTML/D3.js generation with interactive features
- **CacheManager**: Persistent resource name caching
- **ResourceOptimizer**: Find optimal resource purchase sets

## Code Standards

### Python Style
- Use type hints (List, Dict, Optional from typing)
- Dataclasses for model objects
- Descriptive variable names (e.g., `equipment_to_resources` not `e2r`)
- French comments/strings acceptable (project is Dofus-related)

### File Organization
```
├── dofusapi.py          # API communication
├── models.py            # Equipment, Resource, ResourceRequirement dataclasses
├── dataprocessor.py     # Graph processing & community detection
├── visualizer.py        # HTML + D3.js report generation
├── visualizer_templates.py  # CSS/HTML templates
├── resourceoptimizer.py # Resource purchase optimization
├── utils.py             # CacheManager, ExclusionManager
├── config.py            # Config constants
└── visualizations/      # Output HTML files
```

## Common Patterns

### Working with Equipment Groups
```python
# Groups are dicts with structure:
{
    'equipments': [Equipment objects or dicts],
    'total_ingredients': {resource_id: {'name': str, 'total_quantity': int, 'quantity_per_equipment': {}}},
    'unique_ingredients_count': int,
    'total_items_needed': int,
    'sharing_efficiency': float (0-1)
}
```

### Graph Operations
- Equipment similarity: Jaccard coefficient of recipe resources
- Bipartite graph: Equipment (bipartite=0) ↔ Resources (bipartite=1)
- Community detection: Louvain with resolution tuning
- Node filtering: Remove singletons with `min_component_size`

### Visualization Output
- Each group → separate HTML file with:
  - Interactive D3.js force-directed graph
  - Equipment preview (small images + names)
  - Ingredient table (resource × equipment matrix)
  - Statistics cards (efficiency, quantities)
- Index page linking all groups

## Key Metrics
- **Sharing Efficiency**: (Shared Resources) / (Unique Resources) × 100%
- **Resource Overlap**: Jaccard similarity between equipment recipes
- **Equipment Count**: Size of community
- **Items Per Resource**: Average quantities needed

## Frequent Tasks

### Adding a New Grouping Algorithm
1. Add method to `DataProcessor` class
2. Return `List[Dict]` matching group structure
3. Test with sample data from notebooks
4. Call from `main.py` or notebooks

### Improving Visualizations
1. Modify CSS in `visualizer_templates.py`
2. Update D3.js logic in `create_proper_visualization_html()`
3. Test with `generate_visualizations(groups, resource_info_getter)`
4. Check output in `visualizations/` folder

### Adding API Fields
1. Update `Config.FIELDS` in `config.py`
2. Extend `Equipment.from_raw()` in `models.py`
3. Update caching in `utils.py` if needed

## Debugging Tips
- Use notebooks (`equipment_matching.ipynb`, `data_explore.ipynb`) for exploratory work
- Check `resource_cache.json` for cached API responses
- Visualizations output to `visualizations/` → open `index.html` at `http://localhost:8000`
- Print group structure to understand data shape: `print(json.dumps(group, default=str, indent=2))`

## External Dependencies
- `requests`: API calls
- `networkx`: Graph algorithms
- `community-louvain`: Community detection (Louvain)
- `pandas`, `numpy`: Data analysis
- `plotly`: Interactive charts (optional, notebooks only)
- D3.js v7: Loaded from CDN in HTML

## Conventions
- Resource IDs & Equipment IDs: Integer `ankama_id` from API
- French strings: Equipment/resource names are in French
- Image URLs: dict with keys `icon`, `sd`, `small`, `thumbnail`
- Quantities: Always integers (units of resource)
- Efficiency metrics: Floats in range [0, 1], displayed as percentages

---

**Last Updated**: When creating new features, keep this file in sync with architectural changes.