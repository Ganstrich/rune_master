# Module: Visualization Roadmap

## 1. Executive Summary & Purpose
- **Core Function:** Outlines planned improvements and new features for the RuneMaster visual reporting interfaces. It divides features into structural foundations, core interactive charts, dashboard navigation, crafting planners, UX polish, and advanced comparisons.
- **Target Audience/Users:** Front-end developers and automated coding agents.
- **Design Philosophy:** Clean separations, highly interactive visual experiences, and zero external build pipeline dependencies.

## 2. Architectural & Structural Dependencies
- **Parent System/Universe:** RuneMaster
- **Inbound Dependencies:** None (planning document).
- **Outbound Dependencies:**
  - [visualization/VISUALIZATION.md](file:///home/adamb/rune_master/visualization/VISUALIZATION.md) (targets CSS/JS files and generators).
  - D3.js v7 CDN.
- **Interactions/Data Flow:**
  Outlines features where data from the processing layers (group metrics, efficiency, densities) is fed to D3.js visualization scripts to render heatmaps, scatter plots, and histograms.

## 3. Strict Rules & Mechanics (The "Hard Constraints")
| Parameter/State | Rule / Constraint | Logical Consequence |
| :--- | :--- | :--- |
| Build Pipeline | Must remain dependency-free | No npm or Webpack/Vite bundlers can be introduced |
| D3.js Version | Target version must be D3.js v7 | Use CDN link `https://d3js.org/d3.v7.min.js` |
| Asset Extraction | CSS/JS templates must be moved to static files | HTMLGenerator copies them from static folders on generation |

## 4. Key Concepts & Terminology
- **Force-Directed Graph:** Physics simulation showcasing equipment-resource recipe link overlaps.
- **Heatmap:** Row/column correlation matrix displaying item-ingredient quantities.
- **"What If" Mode:** Interactive simulation allowing items to be client-side disabled and metrics dynamically updated.

## 5. Known Gaps & Future Extensions
- **Established Backlog:** CSS/JS splitting (1.1), D3 force-directed graph (2.1), resource heatmap (2.2), scatter plot dashboard (3.1), index search/filter (3.2), related groups navigation (3.3), crafting cost summary (4.1), levels distribution (4.2), shopping list copy/export (4.3), dark mode (5.2), index pagination (5.3).
- **[PROPOSITION]:** Side-by-side group comparison (6.1), "What If" simulation mode (6.2).
