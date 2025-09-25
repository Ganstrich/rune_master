# Centralized CSS templates for visualizer
# Keep these separate to make it easier to iterate on styling without
# touching the main Python logic.

CSS_GRAPH = r"""
<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
    color: #2d3748;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    overflow: hidden;
}

.header {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    color: white;
    padding: 30px 40px;
}

.header h1 {
    font-size: 28px;
    margin-bottom: 8px;
    font-weight: 600;
}

.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-top: 20px;
}

.stat-card {
    background: rgba(255,255,255,0.1);
    padding: 15px;
    border-radius: 8px;
    text-align: center;
    backdrop-filter: blur(10px);
}

.stat-value {
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 5px;
}

.content-area {
    padding: 30px 40px;
}

.layout {
    display: grid;
    /* Single column layout: graph uses full width. Ingredient table is placed above the graph. */
    grid-template-columns: 1fr;
    gap: 18px;
    margin-top: 12px;
}

.graph-section {
    background: #f8fafc;
    border-radius: 8px;
    padding: 20px;
    border: 1px solid #e2e8f0;
}

.ingredient-section {
    background: #f8fafc;
    border-radius: 8px;
    padding: 20px;
    border: 1px solid #e2e8f0;
    max-height: 600px;
    overflow-y: auto;
}

.ingredient-table-container h3 {
    margin-bottom: 15px;
    color: #2d3748;
    border-bottom: 2px solid #4f46e5;
    padding-bottom: 8px;
}

.ingredient-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.ingredient-table th {
    background: #4f46e5;
    color: white;
    padding: 12px;
    text-align: left;
    font-weight: 600;
}

.ingredient-table td {
    padding: 8px 10px;
    border-bottom: 1px solid #e2e8f0;
}

.ingredient-img {
    width: 28px;
    height: 28px;
    object-fit: cover;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.ingredient-table th, .ingredient-table td { font-size: 12px; }
.ingredient-table { font-size: 12px; }

.ingredient-table tr:hover {
    background: #f7fafc;
}

.controls {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
    flex-wrap: wrap;
}

.btn {
    padding: 10px 16px;
    border: none;
    border-radius: 6px;
    background: #4f46e5;
    color: white;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
}

.btn:hover {
    background: #4338ca;
    transform: translateY(-1px);
}

.btn-secondary {
    background: #64748b;
}

.btn-secondary:hover {
    background: #475569;
}

.graph-container {
    width: 100%;
    height: 500px;
    background: white;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
}

.tooltip {
    position: absolute;
    background: rgba(0,0,0,0.9);
    color: white;
    padding: 12px;
    border-radius: 6px;
    pointer-events: none;
    font-size: 13px;
    z-index: 1000;
    max-width: 300px;
}

.node {
    stroke: #fff;
    stroke-width: 2px;
    cursor: pointer;
    transition: all 0.2s;
}

.node.equipment {
    fill: #4f46e5;
}

.node.resource {
    fill: #10b981;
}

.node:hover {
    stroke-width: 3px;
    filter: brightness(1.1);
}

/* Images for resource nodes */
.node-image {
    pointer-events: none; /* events handled on parent group */
    image-rendering: crisp-edges;
    border-radius: 6px;
}

.node-bg {
    stroke: #fff;
    stroke-width: 2px;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.08));
}

/* Image gallery preview used for debugging icons */
.image-gallery {
    margin: 18px 0;
}
.gallery-grid {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
}
.gallery-item {
    width: 64px;
    text-align: center;
    font-size: 12px;
    color: #334155;
}
.gallery-item img {
    width: 48px;
    height: 48px;
    object-fit: cover;
    border-radius: 6px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
.gallery-item .caption { margin-top: 6px; }


.link {
    stroke: #94a3b8;
    stroke-width: 2;
}

.link-label {
    font-size: 11px;
    font-weight: bold;
    fill: #475569;
}

.node-label {
    font-size: 11px;
    font-weight: 600;
    fill: white;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
    pointer-events: none;
}

.legend {
    display: flex;
    gap: 20px;
    margin-bottom: 15px;
    padding: 10px;
    background: white;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
}

.legend-color {
    width: 16px;
    height: 16px;
    border-radius: 50%;
}

.equipment-color { background: #4f46e5; }
.resource-color { background: #10b981; }

.back-link {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: #4f46e5;
    text-decoration: none;
    font-weight: 500;
    margin-bottom: 20px;
    padding: 8px 16px;
    border-radius: 6px;
    background: #f1f5f9;
    transition: all 0.2s;
}

.back-link:hover {
    background: #e2e8f0;
    transform: translateX(-2px);
}

/* Responsive */
@media (max-width: 1024px) {
    .layout {
        grid-template-columns: 1fr;
    }
    
    .header {
        padding: 20px;
    }
    
    .content-area {
        padding: 20px;
    }
}
</style>
"""

CSS_INDEX = r"""
<style>
    body { 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
        margin: 40px; 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    .container { 
        max-width: 800px; 
        margin: 0 auto; 
        background: white; 
        padding: 40px; 
        border-radius: 12px; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    h1 { 
        color: #2d3748; 
        text-align: center; 
        margin-bottom: 30px;
    }
    .group-list { 
        list-style: none; 
        padding: 0; 
    }
    .group-item { 
        background: #f8fafc; 
        margin: 15px 0; 
        padding: 20px; 
        border-radius: 8px; 
        border-left: 4px solid #4f46e5;
    }
    .group-link { 
        text-decoration: none; 
        color: #2d3748; 
        font-weight: 600; 
        font-size: 18px;
        display: block;
        margin-bottom: 8px;
    }
    .group-stats { 
        color: #64748b; 
        font-size: 14px;
    }
</style>
"""
