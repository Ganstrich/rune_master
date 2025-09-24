from flask import Flask, render_template, jsonify
import plotly
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import pandas as pd
from collections import defaultdict
from dataprocessor import DataProcessor 
from dofusapi import DofusAPI

from utils import CacheManager
from config import Config


app = Flask(__name__)

def create_interactive_dashboard(groups, equipments, excluded_resource_ids=None):
    """
    Create an interactive dashboard for equipment groups with resource details
    """
    if excluded_resource_ids is None:
        excluded_resource_ids = set()
    
    # Prepare data for visualization
    dashboard_data = {
        'groups': [],
        'resources': defaultdict(int),
        'equipment_count': len(equipments),
        'group_count': len(groups)
    }
    
    # Process each group
    for i, group in enumerate(groups):
        group_data = {
            'id': i + 1,
            'equipment_count': len(group['equipments']),
            'equipment_names': [e['name'] for e in group['equipments']],
            'equipment_levels': [e['level'] for e in group['equipments']],
            'shared_resources_count': group['shared_resources_count'],
            'sharing_efficiency': group['sharing_efficiency'],
            'resources': defaultdict(int),
            'shared_resources': []
        }
        
        # Calculate resources needed for this group
        for equipment in group['equipments']:
            for resource in equipment['recipe']:
                resource_id = resource['item_ankama_id']
                quantity = resource['quantity']
                group_data['resources'][resource_id] += quantity
                dashboard_data['resources'][resource_id] += quantity
        
        # Identify shared resources
        resource_usage = defaultdict(int)
        for equipment in group['equipments']:
            for resource in equipment['recipe']:
                resource_id = resource['item_ankama_id']
                if resource_id not in excluded_resource_ids:
                    resource_usage[resource_id] += 1
        
        for resource_id, count in resource_usage.items():
            if count > 1:  # Shared by multiple equipment
                resource_name = CacheManager.get_resource_name(resource_id)
                group_data['shared_resources'].append({
                    'id': resource_id,
                    'name': resource_name,
                    'count': count
                })
        
        dashboard_data['groups'].append(group_data)
    
    return dashboard_data

def create_group_visualizations(dashboard_data):
    """
    Create Plotly visualizations for the equipment groups
    """
    # Prepare data for visualizations
    group_ids = [f"Group {g['id']}" for g in dashboard_data['groups']]
    equipment_counts = [g['equipment_count'] for g in dashboard_data['groups']]
    shared_counts = [g['shared_resources_count'] for g in dashboard_data['groups']]
    efficiency_scores = [g['sharing_efficiency'] for g in dashboard_data['groups']]
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Equipment per Group', 'Shared Resources per Group',
                       'Sharing Efficiency', 'Resource Distribution'),
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "pie"}]]
    )
    
    # Equipment count per group
    fig.add_trace(
        go.Bar(x=group_ids, y=equipment_counts, name="Equipment Count",
               marker_color=px.colors.qualitative.Set1),
        row=1, col=1
    )
    
    # Shared resources per group
    fig.add_trace(
        go.Bar(x=group_ids, y=shared_counts, name="Shared Resources",
               marker_color=px.colors.qualitative.Set2),
        row=1, col=2
    )
    
    # Sharing efficiency
    fig.add_trace(
        go.Bar(x=group_ids, y=efficiency_scores, name="Sharing Efficiency",
               marker_color=px.colors.qualitative.Set3),
        row=2, col=1
    )
    
    # Resource distribution (top 10 resources)
    sorted_resources = sorted(dashboard_data['resources'].items(), 
                             key=lambda x: x[1], reverse=True)[:10]
    resource_names = [CacheManager.get_resource_name(rid) for rid, _ in sorted_resources]
    resource_counts = [count for _, count in sorted_resources]
    
    fig.add_trace(
        go.Pie(labels=resource_names, values=resource_counts, name="Resource Distribution"),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        title_text="Equipment Groups Analysis",
        height=800,
        showlegend=True
    )
    
    # Convert to JSON for rendering in HTML
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return graphJSON

@app.route('/')
def index():
    """
    Main dashboard page
    """
    # Your equipment data here
    equipments = DofusAPI.get_all_equipments()
    
    # Define resources to exclude from sharing calculation
    excluded_resources = {2611, 12737, 648}  # Example resource IDs
    
    # Find optimized groups
    groups = DataProcessor().find_optimized_equipment_groups(
        equipments,
        min_shared_resources=2,
        excluded_resource_ids=excluded_resources,
        resolution=1.2,
        min_group_size=2,
        max_group_size=6,
        efficiency_threshold=0.25
    )
    
    # Prepare dashboard data
    dashboard_data = create_interactive_dashboard(groups, equipments, excluded_resources)
    
    # Create visualizations
    graphJSON = create_group_visualizations(dashboard_data)
    
    return render_template('dashboard.html', 
                         graphJSON=graphJSON,
                         dashboard_data=dashboard_data,
                         groups=groups)

@app.route('/group/<int:group_id>')
def group_details(group_id):
    """
    Detailed view for a specific group
    """
    # Your equipment data here
    equipments = DofusAPI.get_all_equipments()
    
    # Find optimized groups
    groups = DataProcessor().find_optimized_equipment_groups(
        equipments,
        min_shared_resources=2,
        excluded_resource_ids=Config.EXCLUDED_RESOURCES,
        resolution=1.2,
        min_group_size=2,
        max_group_size=6,
        efficiency_threshold=0.25
    )
    
    # Find the requested group
    group = None
    for g in groups:
        if g['id'] == group_id:
            group = g
            break
    
    if not group:
        return "Group not found", 404
    
    # Calculate detailed resource information
    resource_details = defaultdict(list)
    total_resources = defaultdict(int)
    
    for equipment in group['equipments']:
        for resource in equipment['recipe']:
            resource_id = resource['item_ankama_id']
            quantity = resource['quantity']
            resource_name = CacheManager.get_resource_name(resource_id)
            
            resource_details[resource_id].append({
                'equipment_name': equipment['name'],
                'quantity': quantity
            })
            
            total_resources[resource_id] += quantity
    
    # Prepare data for rendering
    detailed_resources = []
    for resource_id, usages in resource_details.items():
        resource_name = CacheManager.get_resource_name(resource_id)
        detailed_resources.append({
            'id': resource_id,
            'name': resource_name,
            'total_quantity': total_resources[resource_id],
            'used_by': len(usages),
            'usages': usages
        })
    
    # Sort by total quantity
    detailed_resources.sort(key=lambda x: x['total_quantity'], reverse=True)
    
    return render_template('group_details.html',
                         group=group,
                         resources=detailed_resources)


if __name__ == '__main__':
    app.run(debug=True)