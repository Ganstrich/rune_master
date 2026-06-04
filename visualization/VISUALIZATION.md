# Visualization Module

Generates interactive HTML/CSS/JS reports for equipment groups using D3.js for graph visualization.

## Architecture

```
visualization/
├── html_generator.py     - Core HTML page generation
├── style_templates.py    - CSS and JavaScript templates
└── graph_generator.py    - D3.js force-directed graph
```

## HTML Generator (`html_generator.py`)

### `HTMLGenerator`
Creates complete HTML pages for equipment groups and index dashboard.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `generate_group_page(group)` | Single group detail page |
| `save_group_page(group, path)` | Save group page to disk |
| `generate_index_page(groups)` | Index dashboard with group cards |
| `save_index_page(groups, path)` | Save index to disk |
| `generate_all(groups)` | Generate all pages, return file paths |

**Page Structure (Group Detail):**
1. **Header** - Group title, efficiency badge, metadata
2. **Stats Summary** - Equipment count, shared resources, efficiency
3. **Equipment Gallery** - Cards with images, names, levels
4. **Ingredient Table** - Aggregated recipe requirements
5. **Relationship Graph** - D3.js force-directed visualization

**Page Structure (Index Dashboard):**
1. **Summary Statistics** - Total groups, equipment, avg efficiency
2. **Group Cards** - Sortable cards linking to detail pages
3. **Filtering** - By efficiency, size, method (client-side JS)

## Style Templates (`style_templates.py`)

### CSS Functions

| Function | Description |
|----------|-------------|
| `get_base_css()` | Core layout, typography, variables |
| `get_group_css()` | Group detail page styles |
| `get_index_css()` | Dashboard/card grid styles |

**Design System:**
- CSS custom properties for theming
- Mobile-responsive breakpoints
- Accessible color contrast
- Dark mode support via `prefers-color-scheme`

### JavaScript Utilities

| Function | Description |
|----------|-------------|
| `get_javascript_utils()` | Sorting, filtering, search |

**Features:**
- Client-side table sorting
- Real-time search filtering
- Efficiency threshold slider
- Group size range filter

## Graph Generator (`graph_generator.py`)

### D3.js Force-Directed Graph
Interactive visualization of equipment-resource relationships.

**Features:**
- **Physics simulation** - Force-directed layout with collision detection
- **Drag interaction** - Reposition nodes by dragging
- **Zoom/pan** - Mouse wheel zoom, click-drag pan
- **Tooltips** - Hover for equipment/resource details
- **Responsive** - Auto-resizes with window
- **Color coding** - Blue=Equipment, Green=Resource
- **Node sizing** - Proportional to importance/quantity

**Graph Data Structure:**
```json
{
  "nodes": [
    {"id": 123, "name": "Equipment Name", "type": "equipment", "level": 50},
    {"id": 456, "name": "Resource Name", "type": "resource", "total_quantity": 10}
  ],
  "links": [
    {"source": 123, "target": 456, "quantity": 5}
  ]
}
```

**Key Functions:**
- `get_graph_javascript()` - Returns complete D3.js code block
- `create_graph_html(graph_data)` - Wraps graph in container with data

## Output Structure

```
visualizations/
├── index.html              - Main dashboard
├── group_12345.html        - Individual group pages
├── group_12346.html
└── ...
```

## Performance

- **Generation:** ~5 seconds for 250 groups
- **File Size:** ~2-3 MB total for 250 groups
- **Load Time:** <1 second per page (cached assets)
- **No External Dependencies:** All CSS/JS embedded (except D3.js CDN)

## Design Principles

1. **Self-contained** - All assets embedded in HTML
2. **Progressive enhancement** - Works without JavaScript
3. **Accessible** - ARIA labels, keyboard navigation, color contrast
4. **Responsive** - Mobile-first design
5. **Fast** - Minimal DOM, efficient CSS selectors
