from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from .models import Neo4jConnection, GraphNode, GraphRelationship
import json
import networkx as nx
import plotly.graph_objects as go
import os
import random
import colorsys

# Connect to Neo4j database
def get_db_connection():
    uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    user = os.environ.get('NEO4J_USER', 'neo4j')
    password = os.environ.get('NEO4J_PASSWORD', 'password')
    return Neo4jConnection(uri, user, password)

def index(request):
    return render(request, 'graphapp/index.html')

def add_node(request):
    if request.method == 'POST':
        label = request.POST.get('label')
        name = request.POST.get('name')
        
        # Get additional properties
        properties = {}
        for key, value in request.POST.items():
            if key.startswith('prop_key_') and value:
                prop_id = key.split('_')[-1]
                prop_key = value
                prop_value = request.POST.get(f'prop_value_{prop_id}', '')
                if prop_key and prop_value:
                    properties[prop_key] = prop_value
        
        # Create in Django model
        node = GraphNode.objects.create(
            label=label,
            name=name,
            properties=properties
        )
        
        # Create in Neo4j
        try:
            conn = get_db_connection()
            properties['name'] = name
            result = conn.create_node(label, properties)
            node_id = result[0]['n'].id
            node.node_id = str(node_id)
            node.save()
            conn.close()
        except Exception as e:
            print(f"Error creating Neo4j node: {e}")
        
        return redirect('graph_list')
    
    return render(request, 'graphapp/add_node.html')

def add_relationship(request):
    if request.method == 'POST':
        source_id = request.POST.get('source')
        target_id = request.POST.get('target')
        rel_type = request.POST.get('type')
        
        # Get additional properties
        properties = {}
        for key, value in request.POST.items():
            if key.startswith('prop_key_') and value:
                prop_id = key.split('_')[-1]
                prop_key = value
                prop_value = request.POST.get(f'prop_value_{prop_id}', '')
                if prop_key and prop_value:
                    properties[prop_key] = prop_value
        
        # Create in Django model
        source = GraphNode.objects.get(id=source_id)
        target = GraphNode.objects.get(id=target_id)
        rel = GraphRelationship.objects.create(
            source=source,
            target=target,
            type=rel_type,
            properties=properties
        )
        
        # Create in Neo4j
        try:
            conn = get_db_connection()
            result = conn.create_relationship(
                int(source.node_id), 
                int(target.node_id), 
                rel_type, 
                properties
            )
            rel_id = result[0]['r'].id
            rel.relationship_id = str(rel_id)
            rel.save()
            conn.close()
        except Exception as e:
            print(f"Error creating Neo4j relationship: {e}")
        
        return redirect('graph_list')
    
    nodes = GraphNode.objects.all()
    return render(request, 'graphapp/add_relationship.html', {'nodes': nodes})

def graph_list(request):
    nodes = GraphNode.objects.all()
    relationships = GraphRelationship.objects.all()
    return render(request, 'graphapp/graph_list.html', {
        'nodes': nodes,
        'relationships': relationships
    })

def visualize_graph(request):
    # Get filter parameters from request
    node_type_filter = request.GET.get('node_type', 'all')
    relationship_filter = request.GET.get('relationship', 'all')
    layout_type = request.GET.get('layout', 'kamada_kawai')
    
    # Create a NetworkX graph
    G = nx.DiGraph()
    
    # Add nodes and relationships from Django models
    nodes = GraphNode.objects.all()
    relationships = GraphRelationship.objects.all()
    
    # Apply node type filter if specified
    if node_type_filter != 'all' and node_type_filter:
        nodes = nodes.filter(label=node_type_filter)
    
    # Apply relationship filter if specified
    if relationship_filter != 'all' and relationship_filter:
        relationships = relationships.filter(type=relationship_filter)
    
    # Get all unique node labels for coloring
    node_labels = set(node.label for node in nodes)
    
    # Generate distinct colors for each node label
    colors = generate_distinct_colors(len(node_labels))
    label_colors = dict(zip(node_labels, colors))
    
    # Add nodes with more properties
    for node in nodes:
        # Format properties for display
        formatted_props = "<br>".join([f"<b>{k}:</b> {v}" for k, v in node.properties.items()])
        hover_text = f"<b>Label:</b> {node.label}<br><b>Name:</b> {node.name}"
        if formatted_props:
            hover_text += f"<br><b>Properties:</b><br>{formatted_props}"
            
        G.add_node(
            node.id, 
            label=node.label, 
            name=node.name, 
            properties=node.properties,
            color=label_colors.get(node.label, "#cccccc"),
            hover_text=hover_text
        )
    
    # Get source and target node IDs from the filtered relationships
    related_node_ids = set()
    for rel in relationships:
        related_node_ids.add(rel.source.id)
        related_node_ids.add(rel.target.id)
    
    # If we're filtering relationships, make sure we include the connected nodes
    if relationship_filter != 'all' and relationship_filter:
        # Keep only nodes that are in relationships
        nodes_to_remove = [node_id for node_id in G.nodes() if node_id not in related_node_ids]
        for node_id in nodes_to_remove:
            G.remove_node(node_id)
    
    # Add edges with more data
    for rel in relationships:
        # Only add the edge if both source and target nodes exist in the graph
        if G.has_node(rel.source.id) and G.has_node(rel.target.id):
            # Format properties for display
            formatted_props = "<br>".join([f"<b>{k}:</b> {v}" for k, v in rel.properties.items()])
            hover_text = f"<b>Type:</b> {rel.type}"
            if formatted_props:
                hover_text += f"<br><b>Properties:</b><br>{formatted_props}"
                
            G.add_edge(
                rel.source.id, 
                rel.target.id, 
                type=rel.type, 
                properties=rel.properties,
                hover_text=hover_text
            )
    
    # Choose layout based on selection
    if len(G) == 0:
        # Empty graph, just return empty plot
        return render(request, 'graphapp/visualize.html', {
            'graph_html': None,
            'node_labels': {},
            'relationship_types': set(),
            'selected_layout': layout_type,
            'selected_node_type': node_type_filter,
            'selected_relationship': relationship_filter
        })
    
    # Choose layout based on parameter
    if layout_type == 'spring':
        pos = nx.spring_layout(G, k=0.5, iterations=50)
    elif layout_type == 'circular':
        pos = nx.circular_layout(G)
    else:  # Default to kamada_kawai
        try:
            pos = nx.kamada_kawai_layout(G)
        except:
            # Fallback to spring layout if kamada_kawai fails
            pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    # Create edges with labels and arrows
    edge_traces = []
    
    # All relationship types for legend
    rel_types = set()
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_info = G.get_edge_data(edge[0], edge[1])
        rel_type = edge_info.get('type')
        rel_types.add(rel_type)
        
        # Calculate arrow position (80% along the line)
        arrow_pos = 0.8
        xa = x0 * (1 - arrow_pos) + x1 * arrow_pos
        ya = y0 * (1 - arrow_pos) + y1 * arrow_pos
        
        # Edge line
        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=2, color='#888'),
            hoverinfo='text',
            text=edge_info.get('hover_text'),
            showlegend=False,
            hovertemplate='%{text}<extra></extra>'
        )
        edge_traces.append(edge_trace)
        
        # Edge label (positioned in the middle)
        label_trace = go.Scatter(
            x=[(x0 + x1) / 2],
            y=[(y0 + y1) / 2],
            mode='text',
            text=[rel_type],
            textposition='middle center',
            textfont=dict(size=10, color='#555'),
            hoverinfo='none',
            showlegend=False
        )
        edge_traces.append(label_trace)
        
        # Arrow marker
        arrow_trace = go.Scatter(
            x=[xa],
            y=[ya],
            mode='markers',
            marker=dict(
                symbol='triangle-right',
                size=8,
                color='#888',
                angle=calculate_angle(x0, y0, x1, y1)
            ),
            hoverinfo='none',
            showlegend=False
        )
        edge_traces.append(arrow_trace)
    
    # Create node trace with more interactive features
    node_x = []
    node_y = []
    node_colors = []
    node_sizes = []
    node_texts = []
    node_hovers = []
    node_labels = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_colors.append(G.nodes[node]['color'])
        
        # Size based on connections
        connections = len(list(G.neighbors(node)))
        node_sizes.append(20 + connections * 5)  # Base size plus extra for connections
        
        node_texts.append(G.nodes[node]['name'])
        node_hovers.append(G.nodes[node]['hover_text'])
        node_labels.append(G.nodes[node]['label'])
    
    node_trace = go.Scatter(
        x=node_x, 
        y=node_y,
        mode='markers+text',
        text=node_texts,
        textposition="top center",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='white')
        ),
        hovertemplate='%{customdata}<extra></extra>',
        customdata=node_hovers
    )
    
    # Create the figure with all traces
    fig = go.Figure(
        data=edge_traces + [node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode='closest',
            margin=dict(b=0, l=0, r=0, t=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial"
            ),
            # Drag mode for better interaction
            dragmode='pan',
            modebar=dict(
                orientation='v',
                bgcolor='rgba(255, 255, 255, 0.7)',
            ),
            # Enable interactions
            clickmode='event+select'
        )
    )
    
    # Add buttons to reset zoom and toggle drag mode
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=[
                    dict(
                        args=[{"dragmode": "pan"}],
                        label="Pan",
                        method="relayout"
                    ),
                    dict(
                        args=[{"dragmode": "zoom"}],
                        label="Zoom",
                        method="relayout"
                    ),
                    dict(
                        args=[{"xaxis.autorange": True, "yaxis.autorange": True}],
                        label="Reset Zoom",
                        method="relayout"
                    ),
                ],
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.05,
                y=1.15,
                xanchor="left",
                yanchor="top",
                bgcolor="rgba(255, 255, 255, 0.7)",
                bordercolor="rgba(0, 0, 0, 0.4)",
            ),
        ]
    )
    
    # Extract unique node labels and relationship types for the legend
    unique_labels = {G.nodes[node]['label']: G.nodes[node]['color'] for node in G.nodes()}
    
    # Get all possible node labels and relationship types for filter options
    all_node_labels = {node.label for node in GraphNode.objects.all()}
    all_relationship_types = {rel.type for rel in GraphRelationship.objects.all()}
    
    # Convert to HTML
    graph_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    
    return render(request, 'graphapp/visualize.html', {
        'graph_html': graph_html,
        'node_labels': unique_labels,
        'relationship_types': rel_types,
        'all_node_labels': all_node_labels,
        'all_relationship_types': all_relationship_types,
        'selected_layout': layout_type,
        'selected_node_type': node_type_filter,
        'selected_relationship': relationship_filter
    })

# Helper functions for the visualization
def generate_distinct_colors(n):
    """Generate n visually distinct colors"""
    colors = []
    for i in range(n):
        hue = i / n
        saturation = 0.7 + random.random() * 0.3  # Random between 0.7-1.0
        value = 0.7 + random.random() * 0.3       # Random between 0.7-1.0
        rgb = colorsys.hsv_to_rgb(hue, saturation, value)
        color = f'rgb({int(rgb[0]*255)}, {int(rgb[1]*255)}, {int(rgb[2]*255)})'
        colors.append(color)
    return colors

def calculate_angle(x0, y0, x1, y1):
    """Calculate the angle for arrow markers in degrees"""
    from math import atan2, degrees
    return degrees(atan2(y1 - y0, x1 - x0)) 