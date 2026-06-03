# 🔥 RuneMaster Visualization Roadmap

> Planning file for visualization feature development.
> Each feature has a status: `[ ]` todo, `[x]` done, `[~]` in progress.
> Check off items as you complete them. Re-prioritize as needed.

---

## Phase 1 — Foundation (Structural)

These unblock or simplify everything else.

### 1.1 Split CSS/JS into Static Files
- [ ] Create `visualizations/static/` directory
- [ ] Extract `get_base_css()` → `static/base.css`
- [ ] Extract `get_group_css()` → `static/group.css`
- [ ] Extract `get_index_css()` → `static/index.css`
- [ ] Extract `get_javascript_utils()` → `static/utils.js`
- [ ] Update `HTMLGenerator` to copy static files into output dir on `generate_all()`
- [ ] Replace inline `<style>` and `<script>` tags with `<link>` / `<script src>` references
- [ ] Verify all pages render correctly after the split
- [ ] Run full pipeline end-to-end to confirm

---

## Phase 2 — Core Interactive Visualizations

High-impact features that use data already available in the pipeline.

### 2.1 D3.js Force-Directed Graph (Complete the Stub)
- [ ] Design graph layout: equipment nodes (blue) on left, resource nodes (green) on right
- [ ] Implement force simulation with `d3.forceSimulation`, `d3.forceLink`, `d3.forceCenter`
- [ ] Add drag behavior for nodes
- [ ] Add zoom/pan behavior
- [ ] Style nodes: equipment shows icon image, resource shows icon + name
- [ ] Style links: thickness proportional to quantity, with quantity label
- [ ] Add hover tooltip on nodes (name, level, type / total quantity)
- [ ] Add hover tooltip on links (source → target, quantity)
- [ ] Add legend (equipment vs. resource color coding)
- [ ] Add "reset zoom" button
- [ ] Load D3.js from CDN in `<head>` (add to `get_base_css` or base template)
- [ ] Inject graph data as JSON into the page (from `_build_graph_data`)
- [ ] Wire up `initializeGraph(graphData)` to render into `#graph` div
- [ ] Add graph container to group page template (between header and equipment gallery)
- [ ] Test with small groups (2–3 equipment) and large groups (10+ equipment)
- [ ] Handle edge case: group with no ingredients

### 2.2 Resource Sharing Heatmap
- [ ] Add heatmap container `<div id="heatmap">` to group page template
- [ ] Build heatmap data matrix in `_build_graph_data` or a new method
- [ ] Implement D3.js heatmap: rows = resources, columns = equipment
- [ ] Color scale: white (0) → yellow → orange → red (max quantity)
- [ ] Add axis labels (equipment names on x, resource names on y)
- [ ] Add hover tooltip showing exact quantity
- [ ] Sort resources by total quantity (most shared at top)
- [ ] Add legend for color scale
- [ ] Place below the ingredient table on group detail page

### 2.3 Equipment Stat Weight Visualization
- [ ] Add stat bar chart container to group page template
- [ ] Implement horizontal bar chart (D3 or pure CSS) showing stat_weight per equipment
- [ ] Sort bars by weight (descending)
- [ ] Color bars by equipment type (weapon=red, armor=blue, etc.)
- [ ] Add value labels on bars
- [ ] Add group average line indicator
- [ ] Place in the equipment gallery section

---

## Phase 3 — Dashboard & Navigation

Improve the index page and cross-group navigation.

### 3.1 Group Scatter Plot Dashboard
- [ ] Add scatter plot container to index page template (above or below card grid)
- [ ] Compute per-group: x = sharing_efficiency, y = group_size, r = avg_density
- [ ] Implement D3.js scatter plot with labeled axes
- [ ] Color points by average density (gradient)
- [ ] Add hover tooltip: group number, efficiency, size, equipment names preview
- [ ] Make points clickable → navigate to group detail page
- [ ] Add axis labels and legend
- [ ] Add brush/zoom for dense areas

### 3.2 Index Page Search & Filter
- [ ] Wire up existing search box to filter group cards by equipment name
- [ ] Add range slider for efficiency threshold (min/max)
- [ ] Add range slider for group size (min/max)
- [ ] Add dropdown filter for equipment count
- [ ] Implement real-time filtering (no button needed, filter on input)
- [ ] Show "X of Y groups matching" counter
- [ ] Add "Clear filters" button
- [ ] Persist filter state in URL query params

### 3.3 Related Groups Navigation
- [ ] Compute related groups: groups sharing ≥1 equipment or ≥N resources
- [ ] Add "Related Groups" section at bottom of group detail page
- [ ] Show up to 5 related groups as mini-cards (name, efficiency, shared count)
- [ ] Make mini-cards clickable → navigate to related group page
- [ ] Precompute and inject related groups data into each group page

---

## Phase 4 — Crafting Planning Tools

Features oriented toward actual in-game crafting decisions.

### 4.1 Pod Weight / Crafting Cost Summary
- [ ] Add method to compute total pod weight per group (requires Resource.pods lookup)
- [ ] Add "Crafting Effort" panel to group page (total pods, unique resources, total items)
- [ ] Show pod weight breakdown by resource (bar chart or list)
- [ ] Add pod weight to index page group cards
- [ ] Cache pod weight in group dict during `create_group()`

### 4.2 Level Distribution Chart
- [ ] Add level histogram/violin to group page
- [ ] Show min, max, median level in the group
- [ ] Color bars by level ranges (e.g., 1–50, 51–100, 101–150, 151–200)
- [ ] Add level range indicator to index page group cards

### 4.3 Export / Share Functionality
- [ ] Add "Copy Shopping List" button to group page
- [ ] Format: bulleted list with `Resource x Quantity` per line
- [ ] Show toast notification "Copied to clipboard!"
- [ ] Add "Export CSV" button per group (downloads ingredient list as CSV)
- [ ] Add "Export All Groups CSV" button on index page
- [ ] Add "Copy Group Summary" button (compact text: group name, equipment list, top 5 ingredients)

---

## Phase 5 — Polish & UX

Small improvements that add up.

### 5.1 Equipment Type Icons & Color Coding
- [ ] Map `item_type` values to icon emojis or CSS classes
- [ ] Add type badge to equipment items in gallery
- [ ] Color-code equipment nodes in graph by type
- [ ] Add type breakdown summary to group stats (e.g., "3 Weapons, 2 Armor, 1 Accessory")

### 5.2 Dark Mode Toggle
- [ ] Add toggle button to header (🌙 / ☀️)
- [ ] Persist preference in `localStorage`
- [ ] Apply `.dark-mode` class to `<body>` instead of relying solely on `prefers-color-scheme`
- [ ] Ensure all D3 charts have dark-mode-aware colors

### 5.3 Pagination for Index Page
- [ ] Add pagination controls to index page (20 groups per page)
- [ ] Add "Showing 1–20 of 250 groups" indicator
- [ ] Implement client-side pagination in JS (no server round-trip)
- [ ] Preserve filter state across pages

### 5.4 Responsive Polish
- [ ] Test all new components at 320px, 768px, 1024px, 1440px
- [ ] Ensure graph scales down on mobile (or shows simplified view)
- [ ] Ensure heatmap scrolls horizontally on small screens
- [ ] Add touch-friendly tap targets for mobile

---

## Phase 6 — Advanced (Stretch Goals)

### 6.1 Side-by-Side Group Comparison
- [ ] Add "Compare" checkbox to each group card on index page
- [ ] Add "Compare Selected" button (appears when ≥2 groups selected)
- [ ] Create `compare.html` template with side-by-side layout
- [ ] Show overlapping resources highlighted
- [ ] Show efficiency / size / density comparison bars
- [ ] Show combined shopping list (merged ingredients)

### 6.2 "What If" Mode
- [ ] Add "Remove" button on each equipment in group page
- [ ] Recompute group metrics client-side in JS (efficiency, ingredients, pod weight)
- [ ] Show before/after comparison
- [ ] Add "Reset" button to restore original group
- [ ] Gray out removed equipment visually

---

## Quick Reference: Data Available Per Group

| Field | Type | Source |
|---|---|---|
| `equipments` | `List[Equipment]` | `create_group()` |
| `sharing_efficiency` | `float` | `calculate_shared_resources()` |
| `average_density` | `float` | `calculate_average_density()` |
| `total_ingredients` | `Dict[int, Dict]` | `calculate_total_ingredients()` |
| `shared_resources_count` | `int` | `calculate_shared_resources()` |
| `unique_ingredients_count` | `int` | `len(total_ingredients)` |
| `total_items_needed` | `int` | sum of quantities |
| `group_size` | `int` | `len(equipments)` |
| `fitness_score` | `float` | `evaluate_group()` (committee mode) |

### Equipment Fields Available
- `ankama_id`, `name`, `level`, `type`, `stat_weight`, `effects`, `recipe`, `image_urls`

### Resource Fields Available (from cache)
- `ankama_id`, `name`, `description`, `type`, `level`, `pods`, `image_urls`

---

## Notes

- D3.js v7 is the target version (use CDN: `https://d3js.org/d3.v7.min.js`)
- All D3 code should be in `static/utils.js` or page-specific JS blocks
- Keep the build pipeline dependency-free (no npm, no bundler)
- Test with `python main.py --no-serve` and open the output in a browser
- The `visualizations/` output directory is gitignored — test outputs are ephemeral
