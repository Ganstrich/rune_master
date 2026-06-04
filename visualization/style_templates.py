"""Modern CSS and styling templates for visualization.

This module is deprecated. CSS and JS have been moved to static files:
- visualizations/static/base.css
- visualizations/static/group.css
- visualizations/static/index.css
- visualizations/static/utils.js

Kept for backward compatibility. New code should reference static files directly.
"""


def get_base_css() -> str:
    """Base CSS applied to all pages.
    
    Deprecated: Use static/base.css instead.
    """
    # Read from static file
    import os
    static_path = os.path.join(os.path.dirname(__file__), '..', 'visualizations', 'static', 'base.css')
    try:
        with open(static_path, 'r') as f:
            return f'<style>\n{f.read()}\n</style>'
    except FileNotFoundError:
        return "<!-- base.css not found -->"


def get_group_css() -> str:
    """CSS specific to equipment group visualization pages.
    
    Deprecated: Use static/group.css instead.
    """
    import os
    static_path = os.path.join(os.path.dirname(__file__), '..', 'visualizations', 'static', 'group.css')
    try:
        with open(static_path, 'r') as f:
            return f'<style>\n{f.read()}\n</style>'
    except FileNotFoundError:
        return "<!-- group.css not found -->"


def get_index_css() -> str:
    """CSS for the index/dashboard page showing all groups.
    
    Deprecated: Use static/index.css instead.
    """
    import os
    static_path = os.path.join(os.path.dirname(__file__), '..', 'visualizations', 'static', 'index.css')
    try:
        with open(static_path, 'r') as f:
            return f'<style>\n{f.read()}\n</style>'
    except FileNotFoundError:
        return "<!-- index.css not found -->"


def get_javascript_utils() -> str:
    """Utility JavaScript functions for interactivity.
    
    Deprecated: Use static/utils.js instead.
    """
    import os
    static_path = os.path.join(os.path.dirname(__file__), '..', 'visualizations', 'static', 'utils.js')
    try:
        with open(static_path, 'r') as f:
            return f'<script>\n{f.read()}\n</script>'
    except FileNotFoundError:
        return "<!-- utils.js not found -->"
