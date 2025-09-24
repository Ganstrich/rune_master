# equipment_visualizer.py
import json
import os
from pathlib import Path

class EquipmentVisualizer:
    def __init__(self, output_dir="visualizations"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(exist_ok=True)
    
    def prepare_graph_data(self, group, resource_info_getter=None):
        """Prepare graph data for visualization"""
        nodes = []
        links = []
        node_id_map = {}
        
        # Add equipment nodes
        for equipment in group['equipments']:
            node_id = f"equip_{equipment['ankama_id']}"
            node_id_map[equipment['ankama_id']] = node_id
            nodes.append({
                'id': node_id,
                'name': equipment['name'],
                'type': 'equipment',
                'level': equipment.get('level', 'N/A'),
                'ankama_id': equipment['ankama_id']
            })
        
        # Add resource nodes
        for resource_id, ingredient_info in group['total_ingredients'].items():
            node_id = f"res_{resource_id}"
            node_id_map[resource_id] = node_id
            
            # Get enhanced resource info if available
            resource_info = {}
            if resource_info_getter:
                try:
                    resource_info = resource_info_getter(resource_id) or {}
                except Exception as e:
                    print(f"Warning: Could not fetch info for resource {resource_id}: {e}")
            
            node_data = {
                'id': node_id,
                'name': ingredient_info['name'],
                'type': 'resource',
                'total_quantity': ingredient_info['total_quantity'],
                'ankama_id': resource_id,
                'resource_info': resource_info
            }
            
            # Add common properties
            for prop in ['level', 'type', 'description', 'image_url', 'rarity']:
                if prop in resource_info:
                    node_data[prop] = resource_info[prop]
            
            nodes.append(node_data)
            
            # Create links
            for equip_name, quantity in ingredient_info['quantity_per_equipment'].items():
                equip_node_id = None
                for equipment in group['equipments']:
                    if equipment['name'] == equip_name:
                        equip_node_id = node_id_map[equipment['ankama_id']]
                        break
                
                if equip_node_id:
                    links.append({
                        'source': node_id,
                        'target': equip_node_id,
                        'quantity': quantity
                    })
        
        return {'nodes': nodes, 'links': links}

    def generate_ingredient_table(self, group):
        """Generate a proper HTML table with all ingredients"""
        if not group.get('total_ingredients'):
            return "<p>No ingredient data available</p>"
        
        # Sort by total quantity
        sorted_ingredients = sorted(
            group['total_ingredients'].items(),
            key=lambda x: x[1]['total_quantity'],
            reverse=True
        )
        
        table_rows = []
        for resource_id, ingredient_info in sorted_ingredients:
            # Create usage details
            usage_details = []
            for equip_name, quantity in ingredient_info['quantity_per_equipment'].items():
                usage_details.append(f"{equip_name}: {quantity}")
            
            row = f"""
            <tr>
                <td><strong>{ingredient_info['name']}</strong></td>
                <td style="text-align: center; background: #e8f5e8; font-weight: bold;">{ingredient_info['total_quantity']}</td>
                <td>{'<br>'.join(usage_details)}</td>
            </tr>
            """
            table_rows.append(row)
        
        return f"""
        <div class="ingredient-table-container">
            <h3>📋 Complete Ingredient List</h3>
            <table class="ingredient-table">
                <thead>
                    <tr>
                        <th>Resource</th>
                        <th width="100">Total Needed</th>
                        <th>Used In</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(table_rows)}
                </tbody>
            </table>
        </div>
        """

    def create_proper_visualization_html(self, graph_data, group, group_index):
        """Create a proper interactive visualization with ingredient table"""
        
        graph_data_json = json.dumps(graph_data, indent=2)
        ingredient_table = self.generate_ingredient_table(group)
        
        # Professional CSS that actually works
        css = """
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
    grid-template-columns: 2fr 1fr;
    gap: 30px;
    margin-top: 20px;
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
    padding: 12px;
    border-bottom: 1px solid #e2e8f0;
}

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

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Group {group_index} • Equipment Resource Network</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    {css}
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="index.html" class="back-link">← Back to All Groups</a>
            <h1>Equipment Group {group_index}</h1>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{len(group['equipments'])}</div>
                    <div>Equipment Items</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{group['unique_ingredients_count']}</div>
                    <div>Unique Resources</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{group['total_items_needed']}</div>
                    <div>Total Items Needed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{group['sharing_efficiency']:.1%}</div>
                    <div>Sharing Efficiency</div>
                </div>
            </div>
        </div>
        
        <div class="content-area">
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color equipment-color"></div>
                    <span>Equipment</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color resource-color"></div>
                    <span>Resources</span>
                </div>
            </div>
            
            <div class="controls">
                <button class="btn" onclick="resetLayout()">Reset Layout</button>
                <button class="btn btn-secondary" onclick="toggleLabels()">Toggle Labels</button>
                <button class="btn" onclick="exportData()">Export Data</button>
            </div>
            
            <div class="layout">
                <div class="graph-section">
                    <div class="graph-container" id="graph">
                        <div style="display: flex; justify-content: center; align-items: center; height: 100%; color: #64748b;">
                            Loading interactive network graph...
                        </div>
                    </div>
                </div>
                
                <div class="ingredient-section">
                    {ingredient_table}
                </div>
            </div>
        </div>
    </div>

    <script>
        // Graph data
        const graphData = {graph_data_json};
        
        let simulation;
        let node, link, nodeLabel, linkLabel;
        
        function initializeGraph() {{
            const container = document.getElementById('graph');
            const width = container.clientWidth;
            const height = 500;
            
            // Clear container
            container.innerHTML = '';
            
            // Create SVG
            const svg = d3.select('#graph')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            // Create tooltip
            const tooltip = d3.select('body').append('div')
                .attr('class', 'tooltip')
                .style('opacity', 0);
            
            // Create force simulation
            simulation = d3.forceSimulation(graphData.nodes)
                .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(d => d.type === 'equipment' ? 25 : 20));
            
            // Create links
            link = svg.append('g')
                .selectAll('line')
                .data(graphData.links)
                .enter().append('line')
                .attr('class', 'link')
                .attr('stroke-width', 2);
            
            // Link labels
            linkLabel = svg.append('g')
                .selectAll('text')
                .data(graphData.links)
                .enter().append('text')
                .attr('class', 'link-label')
                .text(d => d.quantity)
                .attr('text-anchor', 'middle');
            
            // Create nodes
            node = svg.append('g')
                .selectAll('circle')
                .data(graphData.nodes)
                .enter().append('circle')
                .attr('class', d => `node ${{d.type}}`)
                .attr('r', d => d.type === 'equipment' ? 20 : 15)
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));
            
            // Node labels
            nodeLabel = svg.append('g')
                .selectAll('text')
                .data(graphData.nodes)
                .enter().append('text')
                .attr('class', 'node-label')
                .text(d => d.name.length > 12 ? d.name.substring(0, 12) + '...' : d.name)
                .attr('text-anchor', 'middle')
                .attr('dy', d => d.type === 'equipment' ? -25 : 20);
            
            // Tooltip content
            function getTooltipContent(d) {{
                let content = `<strong>${{d.name}}</strong><br>`;
                if (d.type === 'equipment') {{
                    content += `Type: Equipment<br>Level: ${{d.level}}`;
                }} else {{
                    content += `Type: Resource<br>Total Needed: ${{d.total_quantity}}`;
                    if (d.level) content += `<br>Level: ${{d.level}}`;
                    if (d.rarity) content += `<br>Rarity: ${{d.rarity}}`;
                }}
                return content;
            }}
            
            // Interactivity
            node.on('mouseover', function(event, d) {{
                // Highlight node
                d3.select(this).attr('r', d.type === 'equipment' ? 25 : 18);
                
                // Highlight connected links
                link.style('stroke', l => 
                    l.source.id === d.id || l.target.id === d.id ? '#ef4444' : '#94a3b8'
                ).style('stroke-width', l => 
                    l.source.id === d.id || l.target.id === d.id ? 3 : 2
                );
                
                // Show tooltip
                tooltip.style('opacity', 1)
                    .html(getTooltipContent(d))
                    .style('left', (event.pageX + 15) + 'px')
                    .style('top', (event.pageY - 15) + 'px');
            }}).on('mouseout', function(event, d) {{
                // Reset node
                d3.select(this).attr('r', d.type === 'equipment' ? 20 : 15);
                
                // Reset links
                link.style('stroke', '#94a3b8').style('stroke-width', 2);
                
                // Hide tooltip
                tooltip.style('opacity', 0);
            }});
            
            // Update positions
            simulation.on('tick', () => {{
                link.attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                linkLabel.attr('x', d => (d.source.x + d.target.x) / 2)
                    .attr('y', d => (d.source.y + d.target.y) / 2);
                
                node.attr('cx', d => d.x)
                    .attr('cy', d => d.y);
                
                nodeLabel.attr('x', d => d.x)
                    .attr('y', d => d.y);
            }});
        }}
        
        // Drag functions
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
        
        // Control functions
        window.resetLayout = function() {{
            if (simulation) {{
                simulation.alphaTarget(0.3).restart();
                graphData.nodes.forEach(d => {{
                    d.fx = null;
                    d.fy = null;
                }});
            }}
        }};
        
        window.toggleLabels = function() {{
            if (nodeLabel) {{
                const current = nodeLabel.style('opacity');
                nodeLabel.style('opacity', current === '1' ? '0' : '1');
                linkLabel.style('opacity', current === '1' ? '0' : '1');
            }}
        }};
        
        window.exportData = function() {{
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(graphData, null, 2));
            const downloadAnchorNode = document.createElement('a');
            downloadAnchorNode.setAttribute("href", dataStr);
            downloadAnchorNode.setAttribute("download", "group_{group_index}_data.json");
            document.body.appendChild(downloadAnchorNode);
            downloadAnchorNode.click();
            downloadAnchorNode.remove();
        }};
        
        // Initialize when D3 is ready
        if (typeof d3 !== 'undefined') {{
            initializeGraph();
        }} else {{
            // Wait for D3 to load
            const checkD3 = setInterval(() => {{
                if (typeof d3 !== 'undefined') {{
                    clearInterval(checkD3);
                    initializeGraph();
                }}
            }}, 100);
        }}
    </script>
</body>
</html>
"""
        
        filename = f"{self.output_dir}/group_{group_index}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        return filename

    def create_index_page(self, groups):
        """Create a simple index page"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Equipment Groups</title>
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
</head>
<body>
    <div class="container">
        <h1>Equipment Group Visualizations</h1>
        <ul class="group-list">
"""
        
        for i, group in enumerate(groups):
            html += f"""
            <li class="group-item">
                <a href="group_{i+1}.html" class="group-link">
                    Group {i+1} - {len(group['equipments'])} Equipment Items
                </a>
                <div class="group-stats">
                    {group['unique_ingredients_count']} resources • {group['total_items_needed']} total items • {group['sharing_efficiency']:.1%} efficiency
                </div>
            </li>
            """
        
        html += """
        </ul>
    </div>
</body>
</html>
"""
        
        with open(f"{self.output_dir}/index.html", 'w', encoding='utf-8') as f:
            f.write(html)

    def generate_visualizations(self, groups, resource_info_getter=None):
        """Generate proper visualizations with all requested features"""
        # Clear the visualizations folder first
        if os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        print(f"🎯 Generating professional visualizations for {len(groups)} groups...")
        
        if not groups:
            print("❌ No groups to visualize.")
            return
        
        # Create individual group pages
        for i, group in enumerate(groups):
            try:
                graph_data = self.prepare_graph_data(group, resource_info_getter)
                filename = self.create_proper_visualization_html(graph_data, group, i+1)
                print(f"✅ Created group_{i+1}.html")
                
            except Exception as e:
                print(f"❌ Error creating visualization for group {i+1}: {e}")
                import traceback
                traceback.print_exc()
        
        # Create index page
        try:
            self.create_index_page(groups)
            print("✅ Created index.html")
        except Exception as e:
            print(f"❌ Error creating index page: {e}")
        
        print(f"\n🎉 Professional visualizations generated!")
        print(f"👉 Open http://localhost:8000/index.html in your browser")
        print(f"📊 Features included:")
        print(f"   • Interactive force-directed graphs")
        print(f"   • Complete ingredient tables with quantities")
        print(f"   • Professional modern design")
        print(f"   • Drag-and-drop interactivity")

# Simple usage
def visualize_equipment_groups(groups, resource_info_getter=None, output_dir="visualizations"):
    """Generate professional equipment group visualizations"""
    visualizer = EquipmentVisualizer(output_dir)
    visualizer.generate_visualizations(groups, resource_info_getter)