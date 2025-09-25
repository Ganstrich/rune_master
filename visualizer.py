# equipment_visualizer.py
import json
import os
from pathlib import Path
from typing import Any
from models import Equipment, Resource
from visualizer_templates import CSS_GRAPH, CSS_INDEX

class EquipmentVisualizer:
    def __init__(self, output_dir="visualizations"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(exist_ok=True)
    
    def prepare_graph_data(self, group, resource_info_getter=None):
        """Prepare graph data for visualization"""
        nodes = []
        links = []
        node_id_map = {}
        
        def _equip_id(equip: Any) -> int:
            if isinstance(equip, Equipment):
                return int(equip.ankama_id)
            if isinstance(equip, dict):
                return int(equip.get('ankama_id'))
            # fallback
            return int(getattr(equip, 'ankama_id', 0))

        def _equip_name(equip: Any) -> str:
            if isinstance(equip, Equipment):
                return equip.name
            if isinstance(equip, dict):
                return equip.get('name')
            return str(getattr(equip, 'name', _equip_id(equip)))

        # Add equipment nodes
        for equipment in group['equipments']:
            eid = _equip_id(equipment)
            node_id = f"equip_{eid}"
            node_id_map[eid] = node_id
            # Try to extract an image URL for equipment (supports Equipment dataclass or raw dict)
            img_url = None
            try:
                if isinstance(equipment, Equipment):
                    imgs = getattr(equipment, 'image_urls', None) or {}
                    if isinstance(imgs, dict):
                        img_url = imgs.get('icon') or imgs.get('sd') or imgs.get('small') or imgs.get('thumbnail')
                    else:
                        # Typed structures may expose attributes
                        img_url = getattr(imgs, 'icon', None)
                elif isinstance(equipment, dict):
                    imgs = equipment.get('image_urls') or {}
                    if isinstance(imgs, dict):
                        img_url = imgs.get('icon') or imgs.get('sd') or imgs.get('small') or imgs.get('thumbnail')
            except Exception:
                img_url = None

            nodes.append({
                'id': node_id,
                'name': _equip_name(equipment),
                'type': 'equipment',
                'level': getattr(equipment, 'level', None) if isinstance(equipment, Equipment) else equipment.get('level', 'N/A') if isinstance(equipment, dict) else getattr(equipment, 'level', 'N/A'),
                'ankama_id': eid,
                'image_url': img_url
            })
        
        # Add resource nodes
        for resource_id, ingredient_info in group['total_ingredients'].items():
            node_id = f"res_{resource_id}"
            node_id_map[resource_id] = node_id
            
            # Get enhanced resource info if available
            resource_info = None
            if resource_info_getter:
                try:
                    resource_info = resource_info_getter(resource_id) or None
                except Exception as e:
                    print(f"Warning: Could not fetch info for resource {resource_id}: {e}")

            # Ensure resource_info is JSON-serializable (convert Resource dataclass to dict)
            def _serialize_resource_info(r):
                if r is None:
                    return None
                if isinstance(r, Resource):
                    # convert dataclass-like fields to plain dict
                    return {
                        'ankama_id': int(r.ankama_id),
                        'name': r.name,
                        'description': r.description,
                        'type': r.type,
                        'level': int(r.level),
                        'pods': int(r.pods),
                        'image_urls': dict(r.image_urls) if r.image_urls else None,
                    }
                if isinstance(r, dict):
                    return r
                # Fallback: try to turn into a string
                try:
                    return dict(r)
                except Exception:
                    return str(r)

            serial_resource_info = _serialize_resource_info(resource_info)

            node_data = {
                'id': node_id,
                'name': ingredient_info.get('name') or (serial_resource_info.get('name') if isinstance(serial_resource_info, dict) else None),
                'type': 'resource',
                'total_quantity': ingredient_info.get('total_quantity', 0),
                'ankama_id': resource_id,
                'resource_info': serial_resource_info
            }

            # Add common properties extracted from resource_info (dataclass or dict)
            if isinstance(resource_info, Resource):
                node_data['level'] = resource_info.level
                # resource_info.type may be a dict-like TypedDict
                node_data['item_type'] = getattr(resource_info, 'type', None)
                node_data['description'] = resource_info.description
                # Prefer icon image if available
                try:
                    # Prefer several fallbacks: icon, sd, small, thumbnail
                    image_urls = resource_info.image_urls or {}
                    node_data['image_url'] = (
                        image_urls.get('icon') or image_urls.get('sd') or image_urls.get('small') or image_urls.get('thumbnail')
                    )
                except Exception:
                    node_data['image_url'] = None
            elif isinstance(resource_info, dict):
                for prop in ['level', 'type', 'description', 'image_url', 'rarity']:
                    if prop in resource_info:
                        node_data[prop] = resource_info[prop]
                # If image_urls dict exists inside resource_info, try common keys
                imgs = resource_info.get('image_urls') or {}
                if not node_data.get('image_url') and isinstance(imgs, dict):
                    node_data['image_url'] = imgs.get('icon') or imgs.get('sd') or imgs.get('small') or imgs.get('thumbnail')
            
            nodes.append(node_data)

            # Create links
            for equip_name, quantity in ingredient_info['quantity_per_equipment'].items():
                equip_node_id = None
                # Find matching equipment by name (works for dataclass or dict)
                for equipment in group['equipments']:
                    if _equip_name(equipment) == equip_name:
                        equip_node_id = node_id_map[_equip_id(equipment)]
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
        # Build a simple image gallery (static <img>) so we can quickly verify images load
        gallery_items = []
        for n in graph_data.get('nodes', []):
            img_url = n.get('image_url') or (n.get('resource_info', {}) or {}).get('image_urls', {}).get('icon')
            if img_url:
                name = n.get('name') or n.get('id')
                # add crossorigin to help debugging CORS issues
                gallery_items.append(f"<div class='gallery-item'><img crossorigin=\"anonymous\" src=\"{img_url}\" alt=\"{name}\" title=\"{name}\"><div class='caption'>{name}</div></div>")

        image_gallery = ''
        if gallery_items:
            image_gallery = f"""
            <div class="image-gallery">
                <h3>Icons Preview</h3>
                <div class="gallery-grid">
                    {''.join(gallery_items)}
                </div>
            </div>
            """
        # Load CSS templates from separate module
        css = CSS_GRAPH

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
            {image_gallery}
            
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
                .attr('height', height)
                .attr('xmlns', 'http://www.w3.org/2000/svg')
                .attr('xmlns:xlink', 'http://www.w3.org/1999/xlink');

            // We'll append inline <image> elements inside each node group. This is simpler
            // and allows the image to move with the node as the simulation runs.
            
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
            
            // Create node groups (so we can put images or circles inside)
            node = svg.append('g')
                .selectAll('g')
                .data(graphData.nodes)
                .enter().append('g')
                .attr('class', d => `node-group ${{d.type}}`)
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));

            // For each node group, append either an image (if available) or a circle
            node.each(function(d) {{
                const g = d3.select(this);
                // background circle for visibility
                g.append('circle')
                    .attr('class', 'node-bg')
                    .attr('r', d.type === 'equipment' ? 22 : 17)
                    .attr('fill', d.type === 'equipment' ? '#4f46e5' : '#10b981');

                if (d.image_url) {{
                    // resource/equipment image (smaller)
                    const w = d.type === 'equipment' ? 40 : 30;
                    const h = w;
                    const img = g.append('image')
                        .attr('class', 'node-image')
                        .attr('width', w)
                        .attr('height', h)
                        .attr('x', -w/2)
                        .attr('y', -h/2)
                        .attr('preserveAspectRatio', 'xMidYMid slice')
                        .attr('href', d.image_url)
                        .attr('xlink:href', d.image_url);

                    // Fallback: if image fails to load, replace with a colored circle
                    try {{
                        const domImg = img.node();
                        if (domImg) {{
                            const probe = new Image();
                            try {{ probe.crossOrigin = 'anonymous'; }} catch(e) {{}}
                            probe.onload = () => {{ /* success */ }};
                            probe.onerror = () => {{
                                d3.select(domImg).remove();
                                g.append('circle')
                                    .attr('class', `node ${{d.type}}`)
                                    .attr('r', d.type === 'equipment' ? 20 : 15);
                            }};
                            probe.src = d.image_url;
                        }}
                    }} catch (e) {{ /* ignore */ }}
                }} else {{
                    // fallback: add a visible node circle (the node-bg already exists but ensure the inner node)
                    g.append('circle')
                        .attr('class', d => `node ${{d.type}}`)
                        .attr('r', d.type === 'equipment' ? 20 : 15);
                }}
                // Add label inside group
                g.append('text')
                    .attr('class', 'node-label')
                    .text(d.name.length > 12 ? d.name.substring(0, 12) + '...' : d.name)
                    .attr('text-anchor', 'middle')
                    .attr('dy', d.type === 'equipment' ? -28 : 24);
            }});

            // Make nodeLabel and linkLabel selections for later toggles
            nodeLabel = svg.selectAll('.node-label');
            
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
                // Enlarge visual (image pattern or circle)
                const g = d3.select(this);
                g.select('circle').attr('r', d.type === 'equipment' ? 25 : 18);

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
                const g = d3.select(this);
                g.select('circle').attr('r', d.type === 'equipment' ? 20 : 15);

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

                // Move node groups
                node.attr('transform', d => `translate(${{d.x}}, ${{d.y}})`);

                // node labels are positioned inside each node group (via dy) so we don't set absolute x/y here.
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
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Equipment Groups</title>
    {CSS_INDEX}
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