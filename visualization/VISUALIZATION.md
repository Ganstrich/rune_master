# Module: Visualization Module

## 1. Executive Summary & Purpose
- **Core Function:** Generates interactive, mobile-responsive HTML/CSS/JS reports representing discovered equipment groups. It provides a visual index dashboard of all groups and detail pages with D3.js force-directed graphs showing equipment-recipe networks.
- **Target Audience/Users:** End-users (players, crafters) and served by the [serve.py](file:///home/adamb/rune_master/serve.py) server.
- **Design Philosophy:** Self-contained reports (all styling/JS assets embedded directly, except CDN-based D3.js), mobile-first responsive layout, and client-side sorting/filtering.

## 2. Architectural & Structural Dependencies
- **Parent System/Universe:** RuneMaster
- **Inbound Dependencies:**
  - [main.py](file:///home/adamb/rune_master/main.py) (starts visual generation after grouping complete).
  - [serve.py](file:///home/adamb/rune_master/serve.py) (runs HTTP web server hosting output pages).
- **Outbound Dependencies:**
  - [processing/PROCESSING.md](file:///home/adamb/rune_master/processing/PROCESSING.md) (uses group lists and schemas).
  - D3.js library (`https://d3js.org/d3.v7.min.js`).
- **Interactions/Data Flow:**
  Takes group dictionaries from the orchestrator -> Feeds records into `html_generator.py` -> Injects style templates and D3 Javascript from `style_templates.py` and `graph_generator.py` -> Writes output `.html` files -> Serves them live to local browser.

### Module Files
- `visualization/html_generator.py` - Core HTML page layout and file generation
- `visualization/style_templates.py` - CSS and client-side Javascript templates
- `visualization/graph_generator.py` - D3.js force-directed graph setup

## 3. Strict Rules & Mechanics (The "Hard Constraints")
| Parameter/State | Rule / Constraint | Logical Consequence |
| :--- | :--- | :--- |
| External Assets | None allowed on local disk | All CSS/JS must be embedded (except D3.js via CDN link) |
| Graph Color Coding | Blue = Equipment, Green = Resource | Visually separates entity types in network nodes |
| Node Sizing | Proportional to importance/quantity | Bigger nodes indicate highly demanded/valuable resources |
| Page Navigation | URLs formatted as `group_[id].html` | Dashboard links depend on matching group IDs |

## 4. Key Concepts & Terminology
- **Force-Directed Graph:** Physics-based simulation rendering nodes with gravity, collision detection, and drag interactions.
- **Index Dashboard:** Main page containing overview statistics (total groups, items, average efficiency) and sorting/filtering sliders.
- **Group Detail Page:** Secondary pages displaying equipment lists, ingredient tables, and interactive network graphs.

## 5. Known Gaps & Future Extensions
- **Established Backlog:**
  - Splitting CSS/JS templates into separate static files, implementing resource heatmaps, and building scatter plots (fully documented in [VISUALIZATION_ROADMAP.md](file:///home/adamb/rune_master/VISUALIZATION_ROADMAP.md)).
- **[PROPOSITION]:** Side-by-side comparison mode, crafting "What If" simulation mode ([VISUALIZATION_ROADMAP.md](file:///home/adamb/rune_master/VISUALIZATION_ROADMAP.md)).
