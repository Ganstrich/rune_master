"""Visualization package - Modern HTML/CSS/JS reports for equipment groups.

Architecture:
- Pure HTML/CSS/JS (no external dependencies beyond D3.js)
- Mobile-responsive and accessible
- Fast loading times
- Professional design patterns

Modules:
- html_generator: Core HTML generation engine
- style_templates: CSS and JavaScript templates
- graph_generator: D3.js force-directed graph visualization
"""

from .html_generator import HTMLGenerator

__all__ = [
    "HTMLGenerator",
]
