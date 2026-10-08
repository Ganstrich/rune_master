"""Core HTML generation engine for equipment group reports.

Responsible for building complete HTML pages from group data, including
equipment galleries, ingredient tables, and summary statistics.
"""
import html
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from models import Equipment
from processing.blocks.shopping_list import ShoppingList
from processing.valuation.focus import break_density
from processing.exploration import ExplorationCandidate


class HTMLGenerator:
    """Generate modern, responsive HTML reports from equipment groups.
    
    Architecture:
    - Pure HTML/CSS/JS (no frameworks)
    - Accessibility-first (WCAG 2.1 AA)
    - Mobile-responsive
    - Fast loading times
    - Static CSS/JS files for caching and maintainability
    """
    
    def __init__(
        self, output_dir: str = "visualizations", manifest: Dict[str, Any] | None = None
    ):
        """Initialize generator.
        
        Args:
            output_dir: Directory to write HTML files to
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.static_dir = self.output_dir / "static"
        self.manifest = manifest or {}

    def generate_exploration_shortlist(
        self, candidates: list[ExplorationCandidate]
    ) -> Path:
        """Write a compact shortlist page with the manual-record command."""
        rows = "".join(
            f"<tr><td>{candidate.item_name}</td><td>{candidate.theoretical_break_density:.2f}</td>"
            f"<td>{candidate.observation_count}</td><td>{candidate.exploration_score:.2f}</td>"
            f"<td><code>{candidate.record_command}</code></td></tr>"
            for candidate in candidates
        )
        path = self.output_dir / "exploration-shortlist.html"
        path.write_text(
            "<h1>Break exploration shortlist</h1><table>"
            "<tr><th>Item</th><th>Density</th><th>Observations</th>"
            f"<th>Score</th><th>Record</th></tr>{rows}</table>",
            encoding="utf-8",
        )
        return path
    
    def _copy_static_files(self):
        """Copy static CSS and JS files to output directory.
        
        This ensures the output directory is self-contained.
        """
        # Get the source static directory (relative to this file)
        source_static = Path(__file__).parent / "static"
        
        if source_static.exists():
            # Create output static directory
            self.static_dir.mkdir(exist_ok=True)
            
            # Copy all files from source to output
            for file_path in source_static.iterdir():
                if file_path.is_file():
                    dest_path = self.static_dir / file_path.name
                    shutil.copy2(file_path, dest_path)
    
    @staticmethod
    def _escape_html(text: Any) -> str:
        """Safely escape HTML to prevent XSS.
        
        Args:
            text: Text to escape
            
        Returns:
            HTML-safe escaped string
        """
        if text is None:
            return ""
        return html.escape(str(text), quote=True)
    
    @staticmethod
    def _escape_attr(text: Any) -> str:
        """Escape HTML for use in attributes only.
        
        Args:
            text: Text to escape
            
        Returns:
            HTML-safe escaped string for attributes
        """
        if text is None:
            return ""
        return html.escape(str(text), quote=True)
    
    @staticmethod
    def _extract_equipment_id(equipment: Any) -> int:
        """Extract ankama_id from Equipment (dataclass or dict).
        
        Args:
            equipment: Equipment dataclass or dict
            
        Returns:
            Ankama ID as integer
        """
        if isinstance(equipment, Equipment):
            return int(equipment.ankama_id)
        elif isinstance(equipment, dict):
            return int(equipment.get('ankama_id', 0))
        else:
            return int(getattr(equipment, 'ankama_id', 0))
    
    @staticmethod
    def _extract_equipment_name(equipment: Any) -> str:
        """Extract name from Equipment (dataclass or dict).
        
        Args:
            equipment: Equipment dataclass or dict
            
        Returns:
            Equipment name
        """
        if isinstance(equipment, Equipment):
            return equipment.name
        elif isinstance(equipment, dict):
            return equipment.get('name', 'Unknown')
        else:
            return getattr(equipment, 'name', 'Unknown')
    
    @staticmethod
    def _extract_equipment_level(equipment: Any) -> int:
        """Extract level from Equipment.
        
        Args:
            equipment: Equipment dataclass or dict
            
        Returns:
            Equipment level
        """
        if isinstance(equipment, Equipment):
            return equipment.level
        elif isinstance(equipment, dict):
            return equipment.get('level', 0)
        else:
            return getattr(equipment, 'level', 0)
    
    @staticmethod
    def _extract_image_url(equipment: Any) -> Optional[str]:
        """Extract image URL from Equipment.
        
        Args:
            equipment: Equipment dataclass or dict
            
        Returns:
            Image URL or None
        """
        try:
            if isinstance(equipment, Equipment):
                urls = equipment.image_urls
                if urls:
                    return urls.get('icon') or urls.get('sd')
            elif isinstance(equipment, dict):
                urls = equipment.get('image_urls', {})
                if urls:
                    return urls.get('icon') or urls.get('sd')
        except (AttributeError, TypeError, KeyError):
            pass
        return None
    
    def _build_equipment_gallery(self, group: Dict[str, Any]) -> str:
        """Build equipment preview gallery HTML.
        
        Shows all equipment in the group with icons.
        
        Args:
            group: Equipment group dict
            
        Returns:
            HTML string
        """
        equipments = group.get('equipments', [])
        if not equipments:
            return ""
        
        items_html = []
        for equipment in equipments:
            name = self._extract_equipment_name(equipment)
            level = self._extract_equipment_level(equipment)
            image_url = self._extract_image_url(equipment)
            
            # Extract stat weight if available
            stat_weight = 0
            if isinstance(equipment, Equipment):
                stat_weight = equipment.stat_weight or 0
            elif isinstance(equipment, dict):
                stat_weight = equipment.get('stat_weight', 0)
            else:
                stat_weight = getattr(equipment, 'stat_weight', 0)
            item_break_density = break_density(equipment) if isinstance(equipment, Equipment) else 0.0
            
            if image_url:
                img_html = f'<img class="equipment-item-image" src="{self._escape_html(image_url)}" alt="{name}">'
            else:
                img_html = '<div class="equipment-item-fallback">⚔️</div>'
            
            items_html.append(f"""
            <div class="equipment-item">
                {img_html}
                <div class="equipment-item-name" data-copy-text="{self._escape_html(name)}">{name}</div>
                <div class="text-tiny text-muted">Lvl {level}</div>
                <div class="equipment-item-weight">⚖️ {stat_weight:.1f}</div>
                <div class="text-tiny text-muted">Break density {item_break_density:.1f}</div>
            </div>
            """)
        
        return f"""
        <div class="equipment-gallery">
            <h3>🛡️ Equipment in Group</h3>
            <div class="equipment-list">
                {''.join(items_html)}
            </div>
        </div>
        """
    
    def _build_ingredient_table(self, group: Dict[str, Any]) -> str:
        """Build ingredient table HTML.
        
        Shows complete ingredient list with per-equipment breakdown.
        
        Args:
            group: Equipment group dict
            
        Returns:
            HTML string for table
        """
        equipments = group.get('equipments', [])
        ingredients = group.get('total_ingredients', {})
        
        if not ingredients:
            return '<div class="ingredient-section"><p>No ingredients data</p></div>'
        
        # Get equipment names
        equipment_names = [self._extract_equipment_name(eq) for eq in equipments]
        
        # Build equipment column headers
        equip_headers = ''.join([
            f'<th>{self._escape_html(name)}</th>'
            for name in equipment_names
        ])
        
        # Sort ingredients by total quantity (descending)
        sorted_ingredients = sorted(
            ingredients.items(),
            key=lambda x: x[1].get('total_quantity', 0),
            reverse=True
        )
        
        # Build table rows
        rows_html = []
        for resource_id, info in sorted_ingredients:
            resource_id = int(resource_id)
            name_raw = info.get('name', f'Resource {resource_id}')
            total = info.get('total_quantity', 0)
            qty_per_eq = info.get('quantity_per_equipment', {})
            
            # Resource cell with icon + name
            image_url = info.get('image_url')
            if image_url:
                icon_html = f'<img class="ingredient-resource-icon" src="{self._escape_html(image_url)}" alt="{self._escape_attr(name_raw)}" />'
            else:
                icon_html = '<div class="ingredient-resource-fallback">📦</div>'

            resource_cell = f'<div class="ingredient-resource-name" data-copy-text="{self._escape_attr(name_raw)}">{name_raw}</div>'
            
            # Per-equipment quantities
            per_eq_cells = []
            for eq_name in equipment_names:
                qty = qty_per_eq.get(eq_name)
                if qty and qty > 0:
                    per_eq_cells.append(f'<td class="ingredient-per-equipment">{qty}</td>')
                else:
                    per_eq_cells.append('<td class="ingredient-per-equipment none">-</td>')
            
            rows_html.append(f"""
            <tr>
                <td>
                    <div class="ingredient-resource-cell">
                        {icon_html}
                        {resource_cell}
                    </div>
                </td>
                <td class="ingredient-total">{total}</td>
                {''.join(per_eq_cells)}
            </tr>
            """)
        
        return f"""
        <div class="ingredient-section">
            <h3>📋 Complete Ingredient List</h3>
            <div class="scrollable">
                <table class="ingredient-table">
                    <thead>
                        <tr>
                            <th>Resource</th>
                            <th width="100">Total</th>
                            {equip_headers}
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows_html)}
                    </tbody>
                </table>
            </div>
        </div>
        """
    
    def _build_stats(self, group: Dict[str, Any]) -> str:
        """Build group statistics display.
        
        Args:
            group: Equipment group dict
            
        Returns:
            HTML string with stats
        """
        equipments = group.get('equipments', [])
        shopping_list = ShoppingList.from_equipments(equipments)
        unique_ingredients = shopping_list.line_item_count
        total_items = shopping_list.total_units
        efficiency = group.get('sharing_efficiency', 0)
        average_density = group.get('average_density', 0)
        origin = group.get('origin') or group.get('selection_method', '—')
        
        return f"""
        <div class="group-stats">
            <div class="group-stat">
                <div class="group-stat-label">Equipment Count</div>
                <div class="group-stat-value">{len(equipments)}</div>
            </div>
            <div class="group-stat">
                <div class="group-stat-label">Unique Resources</div>
                <div class="group-stat-value">{unique_ingredients}</div>
            </div>
            <div class="group-stat">
                <div class="group-stat-label">Total Items</div>
                <div class="group-stat-value">{total_items}</div>
            </div>
            <div class="group-stat">
                <div class="group-stat-label">Efficiency</div>
                <div class="group-stat-value">{efficiency:.1%}</div>
            </div>
            <div class="group-stat">
                <div class="group-stat-label">Avg Density</div>
                <div class="group-stat-value">{average_density:.2f}</div>
            </div>
            <div class="group-stat">
                <div class="group-stat-label">Found By</div>
                <div class="group-stat-value">{origin}</div>
            </div>
        </div>
        """
    
    def generate_group_page(self, group: Dict[str, Any], group_index: int) -> str:
        """Generate complete HTML page for single equipment group.
        
        Args:
            group: Equipment group dict with all metadata
            group_index: Group number (1-based)
            
        Returns:
            Complete HTML page as string
        """
        group_num = group_index + 1
        title = f"Equipment Group {group_num}"
        
        # Build all components
        stats = self._build_stats(group)
        equipment_gallery = self._build_equipment_gallery(group)
        
        # Build ingredient table
        ingredient_table = self._build_ingredient_table(group)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Equipment Crafting Groups</title>
    <link rel="stylesheet" href="static/base.css">
    <link rel="stylesheet" href="static/group.css">
</head>
<body>
    <a href="#main" class="skip-link">Skip to main content</a>
    
    <header class="group-header">
        <div class="container-full">
            <div class="flex-between mb-md">
                <h1>{title}</h1>
                <a href="index.html" class="btn btn-secondary">← Back to Dashboard</a>
            </div>
            {stats}
        </div>
    </header>
    
    <main id="main" class="container">
        {equipment_gallery}
        {ingredient_table}
    </main>
    
    <footer style="text-align: center; padding: 2rem; color: var(--color-gray-500); border-top: 1px solid var(--border-color); background: var(--bg-card);">
        <p>Generated by Rune Master | Equipment Crafting Optimizer</p>
    </footer>
    
    <script src="static/utils.js"></script>
</body>
</html>
"""
        return html_content
    
    def save_group_page(self, group: Dict[str, Any], group_index: int) -> str:
        """Generate and save equipment group page.
        
        Args:
            group: Equipment group dict
            group_index: Group number (0-based)
            
        Returns:
            Path to saved file
        """
        html_content = self.generate_group_page(group, group_index)
        
        filename = f"group_{group_index + 1:03d}.html"
        filepath = self.output_dir / filename
        
        filepath.write_text(html_content, encoding='utf-8')
        print(f"✅ Saved {filepath}")
        
        return str(filepath)
    
    def generate_index_page(self, groups: List[Dict[str, Any]]) -> str:
        """Generate index page showing all groups as cards.
        
        Args:
            groups: List of equipment group dicts
            
        Returns:
            Complete HTML page as string
        """
        if not groups:
            cards_html = '<div class="no-results"><div class="no-results-icon">📭</div><p>No equipment groups generated</p></div>'
        else:
            cards_html = self._build_group_cards(groups)
        
        summary_stats = self._build_index_summary(groups)
        group_data = self._build_group_data(groups)
        report_id = self._escape_html(self.manifest.get("run_id", "unidentified"))
        scope = self.manifest.get("scope", {})
        scope_text = self._escape_html(scope.get("summary", "Scope not recorded"))
        cache = self.manifest.get("source", {}).get("cache", {})
        cache_text = self._escape_html(
            f"Resource metadata: {cache.get('status', 'unavailable')}"
        )
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Equipment Groups - Crafting Optimizer</title>
    <link rel="stylesheet" href="static/base.css">
    <link rel="stylesheet" href="static/index.css">
</head>
<body>
    <a href="#main" class="skip-link">Skip to main content</a>
    
    <header class="index-header">
        <div class="container-full">
            <h1>⚔️ Equipment Crafting Groups</h1>
            <p>Optimized equipment combinations for efficient crafting</p>
            <p class="report-meta">Report <code>{report_id}</code> | {scope_text} | {cache_text}</p>
            {summary_stats}
        </div>
    </header>
    
    <main id="main" class="container">
        <section class="combined-list" aria-labelledby="combined-list-title">
            <div class="flex-between">
                <div>
                    <h2 id="combined-list-title">Recipe requirement summary</h2>
                    <p>Select groups to total their ingredients. This is not an inventory or cost estimate.</p>
                </div>
                <button id="copy-combined-list" class="btn btn-secondary" type="button" disabled>Copy list</button>
            </div>
            <p id="combined-list-empty">No groups selected.</p>
            <div id="combined-list-output" hidden></div>
        </section>
        <div class="index-controls" aria-label="Filter and sort groups">
            <label class="sr-only" for="group-search">Filter groups</label>
            <input id="group-search" class="search-box" type="search" placeholder="Filter groups" />
            <label class="sr-only" for="group-sort">Sort groups</label>
            <select id="group-sort" class="sort-select">
                <option value="default">Default ranking</option>
                <option value="efficiency">Sharing efficiency</option>
                <option value="density">Average density</option>
                <option value="size">Group size</option>
                <option value="resources">Shared resources</option>
            </select>
            <button id="group-reset" class="btn btn-secondary" type="button">Reset</button>
        </div>
        <div class="groups-container">
            {cards_html}
        </div>
        <p id="group-empty-state" class="no-results" role="status" hidden>No groups match this filter.</p>
    </main>
    
    <footer style="text-align: center; padding: 2rem; color: var(--color-gray-500); border-top: 1px solid var(--border-color); background: var(--bg-card);">
        <p>Generated by Rune Master | Equipment Crafting Optimizer</p>
    </footer>
    
    <script src="static/utils.js"></script>
    <script type="application/json" id="group-data">{group_data}</script>
</body>
</html>
"""
        return html_content
    
    def _build_group_cards(self, groups: List[Dict[str, Any]]) -> str:
        """Build group cards HTML for index page.
        
        Args:
            groups: List of equipment groups
            
        Returns:
            HTML string with group cards
        """
        cards = []
        for idx, group in enumerate(groups):
            equipments = group.get('equipments', [])
            shopping_list = ShoppingList.from_equipments(equipments)
            efficiency = group.get('sharing_efficiency', 0)
            shared_resources = group.get('shared_resources_count', 0)
            average_density = group.get('average_density', 0)
            total_items = shopping_list.total_units
            
            # Build equipment list
            equip_names = [self._escape_html(self._extract_equipment_name(eq)) for eq in equipments[:5]]
            equip_list = ", ".join(equip_names)
            if len(equipments) > 5:
                equip_list += f", +{len(equipments) - 5} more"
            
            cards.append(f"""
            <div class="group-card" data-rank="{idx + 1}" data-group-file="group_{idx + 1:03d}.html"
                data-efficiency="{efficiency}" data-density="{average_density}"
                data-size="{len(equipments)}" data-resources="{shared_resources}">
                <div class="group-card-header">
                    <label><input class="group-selector" type="checkbox" data-group-id="{idx + 1}"> Select group</label>
                    <div class="group-card-rank">Rank {idx + 1}{' - Highest-ranked' if idx == 0 else ''}</div>
                    <h3 class="group-card-title">Group {idx + 1}</h3>
                </div>
                <div class="group-card-body">
                    <div class="group-card-equipment">
                        <span class="group-card-stat-label">Equipment:</span>
                        <span class="group-card-equipment-list">{equip_list}</span>
                    </div>
                    <div class="group-card-stat">
                        <span class="group-card-stat-label">Group size</span>
                        <span class="group-card-stat-value">{len(equipments)}</span>
                    </div>
                    <div class="group-card-stat">
                        <span class="group-card-stat-label">Shared resources</span>
                        <span class="group-card-stat-value">{shared_resources}</span>
                    </div>
                    <div class="group-card-stat">
                        <span class="group-card-stat-label">Average density</span>
                        <span class="group-card-stat-value">{average_density:.2f}</span>
                    </div>
                    <div class="group-card-stat">
                        <span class="group-card-stat-label">Sharing efficiency</span>
                        <span class="group-card-stat-value">{efficiency:.1%}</span>
                    </div>
                    <div class="group-card-stat">
                        <span class="group-card-stat-label">Total items</span>
                        <span class="group-card-stat-value">{total_items}</span>
                    </div>
                </div>
                <div class="group-card-footer">
                    <a href="group_{idx + 1:03d}.html" class="group-card-link">View Details →</a>
                </div>
            </div>
            """)
        
        return ''.join(cards)

    def _build_group_data(self, groups: List[Dict[str, Any]]) -> str:
        """Serialize only the ingredient data needed for combined totals."""
        data = []
        for index, group in enumerate(groups, start=1):
            resources = {}
            for resource_id, info in group.get("total_ingredients", {}).items():
                resource_key = str(resource_id)
                resources[resource_key] = {
                    "name": info.get("name") or f"Resource {resource_key} (metadata unavailable)",
                    "image_url": info.get("image_url"),
                    "quantity": info.get("total_quantity", 0),
                }
            data.append({"id": str(index), "label": f"Group {index}", "resources": resources})
        return json.dumps(data, ensure_ascii=True).replace("<", "\\u003c")
    
    def _build_index_summary(self, groups: List[Dict[str, Any]]) -> str:
        """Build summary statistics for index page.
        
        Args:
            groups: List of equipment groups
            
        Returns:
            HTML string with summary cards
        """
        total_equipments = sum(len(g.get('equipments', [])) for g in groups)
        total_groups = len(groups)
        avg_efficiency = sum(g.get('sharing_efficiency', 0) for g in groups) / len(groups) if groups else 0
        avg_density = sum(g.get('average_density', 0) for g in groups) / len(groups) if groups else 0
        
        return f"""
        <div class="index-summary">
            <div class="summary-card">
                <div class="summary-label">Total Groups</div>
                <div class="summary-value">{total_groups}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Equipment Analyzed</div>
                <div class="summary-value">{total_equipments}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Average Efficiency</div>
                <div class="summary-value">{avg_efficiency:.1%}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Average Density</div>
                <div class="summary-value">{avg_density:.2f}</div>
            </div>
        </div>
        """
    
    def save_index_page(self, groups: List[Dict[str, Any]]) -> str:
        """Generate and save index page.
        
        Args:
            groups: List of equipment groups
            
        Returns:
            Path to saved index file
        """
        html_content = self.generate_index_page(groups)
        
        filepath = self.output_dir / "index.html"
        filepath.write_text(html_content, encoding='utf-8')
        
        print(f"✅ Saved index page: {filepath}")
        return str(filepath)
    
    def generate_all(self, groups: List[Dict[str, Any]]) -> List[str]:
        """Generate all HTML files (index + group pages).
        
        Args:
            groups: List of equipment groups
            
        Returns:
            List of generated file paths
        """
        files = []
        ranked_groups = self._rank_groups_for_crafting(groups)
        manifest_path = self.write_manifest()
        files.append(manifest_path)
        
        # Copy static files first
        self._copy_static_files()
        
        # Generate individual group pages
        for idx, group in enumerate(ranked_groups):
            filepath = self.save_group_page(group, idx)
            files.append(filepath)
        
        # Generate index page
        index_filepath = self.save_index_page(ranked_groups)
        files.append(index_filepath)

        return files

    def write_manifest(self) -> str:
        """Write the machine-readable metadata beside the generated report."""
        payload = {
            **self.manifest,
            "run_id": self.manifest.get("run_id", uuid4().hex[:12]),
            "generated_at": self.manifest.get(
                "generated_at", datetime.now(timezone.utc).isoformat()
            ),
        }
        path = self.output_dir / "manifest.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self.manifest = payload
        return str(path)

    @staticmethod
    def _rank_groups_for_crafting(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank groups by transparent recipe-sharing evidence for the report."""
        ranked = sorted(
            enumerate(groups),
            key=lambda indexed_group: (
                -indexed_group[1].get("sharing_efficiency", 0.0),
                -indexed_group[1].get("shared_resources_count", 0),
                -indexed_group[1].get("average_density", 0.0),
                -len(indexed_group[1].get("equipments", [])),
                indexed_group[0],
            ),
        )
        return [group for _index, group in ranked]
