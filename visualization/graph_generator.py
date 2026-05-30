"""D3.js force-directed graph visualization for equipment relationships.

Architecture:
- Builds bipartite graph (equipment ↔ resources)
- Uses D3 force simulation for layout
- Responsive and interactive with tooltips
- Color-coded by node type
"""


def get_graph_javascript() -> str:
    r"""Embed D3.js graph visualization code.
    
    Features:
    - Force-directed layout with physics simulation
    - Drag-to-move nodes
    - Zoom and pan
    - Interactive tooltips on hover
    - Responsive sizing
    """
    return r"""
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
/**
 * Initialize D3.js force-directed graph visualization
 * 
 * Displays equipment and resources as nodes, connected by recipe requirements.
 * Node colors: Blue=Equipment, Green=Resource
 * Node size: Proportional to importance/quantity
 */
function initializeGraph(graphDataJson) {
    // Parse graph data
    const graphData = JSON.parse(graphDataJson);
    const { nodes, links } = graphData;
    
    if (!nodes || nodes.length === 0) {
        console.warn('No graph data to visualize');
        return;
    }
    
    const container = document.getElementById('graph');
    if (!container) {
        console.error('Graph container not found');
        return;
    }
    
    // Get container dimensions
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // ========================================================================
    // SVG Setup
    // ========================================================================
    const svg = d3.select('#graph')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', `0 0 ${width} ${height}`)
        .attr('preserveAspectRatio', 'xMidYMid meet');
    
    // Add background
    svg.append('rect')
        .attr('width', width)
        .attr('height', height)
        .attr('fill', '#f9fafb')
        .attr('class', 'graph-background');
    
    // Create main group for zoom/pan
    const g = svg.append('g');
    
    // Add zoom behavior
    const zoom = d3.zoom()
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });
    
    svg.call(zoom);
    
    // ========================================================================
    // Simulation Setup
    // ========================================================================
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links)
            .id(d => d.id)
            .distance(100))
        .force('charge', d3.forceManyBody()
            .strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide(50));
    
    // ========================================================================
    // Links (edges between nodes)
    // ========================================================================
    const link = g.selectAll('line')
        .data(links)
        .enter()
        .append('line')
        .attr('class', 'graph-link')
        .attr('stroke', '#cbd5e1')
        .attr('stroke-width', d => Math.max(1, Math.sqrt(d.quantity)))
        .attr('opacity', 0.6);
    
    // Link labels (quantity)
    const linkLabel = g.selectAll('.link-label')
        .data(links)
        .enter()
        .append('text')
        .attr('class', 'link-label')
        .attr('font-size', '11px')
        .attr('fill', '#94a3b8')
        .attr('text-anchor', 'middle')
        .attr('dy', -4)
        .text(d => d.quantity > 1 ? `×${d.quantity}` : '');
    
    // ========================================================================
    // Nodes (equipment and resources)
    // ========================================================================
    const node = g.selectAll('.node')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded));
    
    // Node circles with color by type
    node.append('circle')
        .attr('r', d => {
            if (d.type === 'equipment') return 25;
            // Resource size based on quantity
            return Math.min(30, 10 + (d.total_quantity || 0) / 10);
        })
        .attr('fill', d => {
            if (d.type === 'equipment') return '#4f46e5';  // Primary blue
            return '#10b981';  // Green for resources
        })
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .attr('opacity', 0.9)
        .style('cursor', 'pointer');
    
    // Node icons/images (if available)
    node.append('image')
        .attr('x', d => -12)
        .attr('y', d => -12)
        .attr('width', 24)
        .attr('height', 24)
        .attr('href', d => d.image_url || '')
        .attr('opacity', d => d.image_url ? 0.8 : 0)
        .attr('clip-path', 'url(#circle-clip)');
    
    // Node labels
    node.append('text')
        .attr('class', 'node-label')
        .attr('text-anchor', 'middle')
        .attr('dy', d => d.type === 'equipment' ? 35 : 40)
        .attr('font-size', '12px')
        .attr('font-weight', 'bold')
        .attr('fill', '#374151')
        .text(d => d.name)
        .style('pointer-events', 'none')
        .style('user-select', 'none');
    
    // ========================================================================
    // Tooltips
    // ========================================================================
    node.append('title')
        .text(d => {
            if (d.type === 'equipment') {
                return `${d.name}\\nLevel: ${d.level}\\nID: ${d.ankama_id}`;
            }
            return `${d.name}\\nQuantity: ${d.total_quantity}\\nID: ${d.ankama_id}`;
        });
    
    // ========================================================================
    // Animation
    // ========================================================================
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        linkLabel
            .attr('x', d => (d.source.x + d.target.x) / 2)
            .attr('y', d => (d.source.y + d.target.y) / 2);
        
        node.attr('transform', d => `translate(\${d.x},\${d.y})`);
    });
    
    // ========================================================================
    // Drag behavior
    // ========================================================================
    function dragStarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragEnded(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
    
    // ========================================================================
    // Legend
    // ========================================================================
    const legend = svg.append('g')
        .attr('class', 'legend')
        .attr('transform', `translate(10, 10)`);
    
    const legendItems = [
        { color: '#4f46e5', label: 'Equipment' },
        { color: '#10b981', label: 'Resource' }
    ];
    
    legendItems.forEach((item, i) => {
        const group = legend.append('g')
            .attr('transform', `translate(0, \${i * 25})`);
        
        group.append('circle')
            .attr('r', 5)
            .attr('fill', item.color);
        
        group.append('text')
            .attr('x', 15)
            .attr('y', 5)
            .attr('font-size', '13px')
            .text(item.label);
    });
    
    // ========================================================================
    // Responsive
    // ========================================================================
    window.addEventListener('resize', () => {
        const newWidth = container.clientWidth;
        const newHeight = container.clientHeight;
        
        svg.attr('width', newWidth)
           .attr('height', newHeight)
           .attr('viewBox', `0 0 \${newWidth} \${newHeight}`);
        
        // Re-center simulation
        simulation
            .force('center', d3.forceCenter(newWidth / 2, newHeight / 2))
            .alpha(0.3)
            .restart();
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const graphDataElement = document.getElementById('graph-data');
    if (graphDataElement) {
        const graphDataJson = graphDataElement.textContent;
        initializeGraph(graphDataJson);
    }
});
</script>
"""


def create_graph_html(graph_data: dict) -> str:
    """Create HTML fragment for graph visualization.
    
    Args:
        graph_data: Dict with 'nodes' and 'links' for D3.js
        
    Returns:
        HTML string with graph container and data
    """
    import json
    
    graph_json = json.dumps(graph_data, indent=2)
    
    return f"""
<div class="graph-container">
    <h3>⚙️ Equipment Relationship Graph</h3>
    <p class="text-small text-muted">
        Blue nodes = Equipment | Green nodes = Resources<br>
        Drag to reposition • Scroll to zoom • Click to focus
    </p>
    <div id="graph"></div>
    <!-- Hidden data for D3.js to consume -->
    <script type="application/json" id="graph-data">
{graph_json}
    </script>
</div>
{get_graph_javascript()}
"""
