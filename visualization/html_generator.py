"""Core HTML generation engine for equipment group reports.

Responsible for:
- Building complete HTML pages from group data
- Coordinating all UI components (graph, table, stats)
- Responsive design and modern UX
- Safe HTML escaping and XSS prevention
"""
import json
import html
from typing import Dict, List, Any, Optional
from pathlib import Path

from models import Equipment, Resource
from .style_templates import (
    get_base_css,
    get_group_css,
    get_index_css,
    get_javascript_utils
)
from .graph_generator import create_graph_html


class HTMLGenerator:
    """Generate modern, responsive HTML reports from equipment groups.
    
    Architecture:
    - Pure HTML/CSS/JS (no frameworks)
    - Accessibility-first (WCAG 2.1 AA)
    - Mobile-responsive
    - Fast loading times
    """
    
    def __init__(self, output_dir: str = "visualizations"):
        """Initialize generator.
        
        Args:
            output_dir: Directory to write HTML files to
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
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
    
    def _build_graph_data(self, group: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Build graph data from equipment group.
        
        Creates nodes for equipment and resources, links for recipe connections.
        
        Args:
            group: Equipment group dict with equipments and total_ingredients
            
        Returns:
            Dict with 'nodes' and 'links' lists for D3.js
        """
        nodes = []
        links = []
        node_id_map = {}
        
        # Add equipment nodes
        for equipment in group.get('equipments', []):
            eq_id = self._extract_equipment_id(equipment)
            node_id = f"equip_{eq_id}"
            node_id_map[eq_id] = node_id
            
            nodes.append({
                'id': node_id,
                'name': self._extract_equipment_name(equipment),
                'type': 'equipment',
                'level': self._extract_equipment_level(equipment),
                'ankama_id': eq_id,
                'image_url': self._extract_image_url(equipment)
            })
        
        # Add resource nodes and links
        for resource_id, ingredient_info in group.get('total_ingredients', {}).items():
            resource_id = int(resource_id)
            node_id = f"res_{resource_id}"
            node_id_map[resource_id] = node_id
            
            nodes.append({
                'id': node_id,
                'name': ingredient_info.get('name', f'Resource {resource_id}'),
                'type': 'resource',
                'total_quantity': ingredient_info.get('total_quantity', 0),
                'ankama_id': resource_id
            })
            
            # Create links from equipment to resources
            for equip_name, quantity in ingredient_info.get('quantity_per_equipment', {}).items():
                # Find matching equipment
                for equipment in group.get('equipments', []):
                    if self._extract_equipment_name(equipment) == equip_name:
                        eq_id = self._extract_equipment_id(equipment)
                        links.append({
                            'source': node_id_map.get(eq_id),
                            'target': node_id,
                            'quantity': quantity
                        })
                        break
        
        return {'nodes': nodes, 'links': links}
    
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
            name = self._escape_html(self._extract_equipment_name(equipment))
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
            name = self._escape_html(info.get('name', f'Resource {resource_id}'))
            total = info.get('total_quantity', 0)
            qty_per_eq = info.get('quantity_per_equipment', {})
            
            # Resource cell with icon + name
            resource_cell = f'<div class="ingredient-resource-name" data-copy-text="{self._escape_html(name)}">{name}</div>'
            
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
        ingredients = group.get('total_ingredients', {})
        unique_ingredients = len(ingredients)
        total_items = sum(i.get('total_quantity', 0) for i in ingredients.values())
        efficiency = group.get('sharing_efficiency', 0)
        
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
        graph_data = self._build_graph_data(group)
        graph_html = create_graph_html(graph_data)
        equipment_gallery = self._build_equipment_gallery(group)
        ingredient_table = self._build_ingredient_table(group)
        stats = self._build_stats(group)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Equipment Crafting Groups</title>
    {get_base_css()}
    {get_group_css()}
</head>
<body>
    <a href="#main" class="skip-link">Skip to main content</a>
    
    <header class="group-header">
        <div class="container-full">
            <h1>{title}</h1>
            {stats}
        </div>
    </header>
    
    <main id="main" class="container">
        {equipment_gallery}
        {ingredient_table}
        {graph_html}
    </main>
    
    <footer style="text-align: center; padding: 2rem; color: var(--color-gray-500); border-top: 1px solid var(--color-gray-200);">
        <p>Generated by Rune Master | Equipment Crafting Optimizer</p>
    </footer>
    
    {get_javascript_utils()}
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
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Equipment Groups - Crafting Optimizer</title>
    {get_base_css()}
    {get_index_css()}
</head>
<body>
    <a href="#main" class="skip-link">Skip to main content</a>
    
    <header class="index-header">
        <div class="container-full">
            <h1>⚔️ Equipment Crafting Groups</h1>
            <p>Optimized equipment combinations for efficient crafting</p>
            {summary_stats}
        </div>
    </header>
    
    <main id="main" class="container">
        <div class="groups-container">
            {cards_html}
        </div>
    </main>
    
    <footer style="text-align: center; padding: 2rem; color: var(--color-gray-500); border-top: 1px solid var(--color-gray-200);">
        <p>Generated by Rune Master | Equipment Crafting Optimizer</p>
    </footer>
    
    {get_javascript_utils()}
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
            ingredients = group.get('total_ingredients', {})
            efficiency = group.get('sharing_efficiency', 0)
            total_items = sum(i.get('total_quantity', 0) for i in ingredients.values())
            
            # Build equipment list
            equip_names = [self._escape_html(self._extract_equipment_name(eq)) for eq in equipments[:5]]
            equip_list = ", ".join(equip_names)
            if len(equipments) > 5:
                equip_list += f", +{len(equipments) - 5} more"
            
            cards.append(f"""
            <div class="group-card">
                <div class="group-card-header">
                    <h3 class="group-card-title">Group {idx + 1}</h3>
                </div>
                <div class="group-card-body">
                    <div class="group-card-equipment">
                        <span class="group-card-stat-label">Equipment:</span>
                        <span class="group-card-equipment-list">{equip_list}</span>
                    </div>
                    <div class="group-card-stat">
                        <span class="group-card-stat-label">Count</span>
                        <span class="group-card-stat-value">{len(equipments)}</span>
                    </div>
                    <div class="group-card-stat">
                        <span class="group-card-stat-label">Resources</span>
                        <span class="group-card-stat-value">{len(ingredients)}</span>
                    </div>
                    <div class="group-card-stat">
                        <span class="group-card-stat-label">Total Items</span>
                        <span class="group-card-stat-value">{total_items}</span>
                    </div>
                    <div class="group-card-stat">
                        <span class="group-card-stat-label">Efficiency</span>
                        <span class="group-card-stat-value">{efficiency:.1%}</span>
                    </div>
                </div>
                <div class="group-card-footer">
                    <a href="group_{idx + 1:03d}.html" class="group-card-link">View Details →</a>
                </div>
            </div>
            """)
        
        return ''.join(cards)
    
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
        
        # Generate individual group pages
        for idx, group in enumerate(groups):
            filepath = self.save_group_page(group, idx)
            files.append(filepath)
        
        # Generate index page
        index_filepath = self.save_index_page(groups)
        files.append(index_filepath)
        
        return files
