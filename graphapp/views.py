from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.contrib import messages
from .models import Neo4jConnection, GraphNode, GraphRelationship
import json
import networkx as nx
import plotly.graph_objects as go
import os
import random
import colorsys
import numpy as np

# Connect to Neo4j database
def get_db_connection():
    uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    user = os.environ.get('NEO4J_USER', 'neo4j')
    password = os.environ.get('NEO4J_PASSWORD', 'password')
    
    # Get connection settings from Django settings if available
    if hasattr(settings, 'NEO4J_URI'):
        uri = settings.NEO4J_URI
    if hasattr(settings, 'NEO4J_USER'):
        user = settings.NEO4J_USER
    if hasattr(settings, 'NEO4J_PASSWORD'):
        password = settings.NEO4J_PASSWORD
        
    connection = Neo4jConnection(uri, user, password)
    return connection

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
            if result and result[0]['n'] is not None:
                node_id = result[0]['n'].id
                node.node_id = str(node_id)
                node.save()
            conn.close()
        except Exception as e:
            print(f"Error creating Neo4j node: {e}")
        
        return redirect('graph_list')
    
    return render(request, 'graphapp/add_node.html')

def delete_node(request, node_id):
    node = get_object_or_404(GraphNode, id=node_id)
    
    # Delete from Neo4j
    try:
        if node.node_id:
            conn = get_db_connection()
            conn.delete_node(int(node.node_id))
            conn.close()
    except Exception as e:
        print(f"Error deleting Neo4j node: {e}")
    
    # Delete from Django
    node_name = node.name
    node.delete()
    
    messages.success(request, f"Node '{node_name}' was successfully deleted along with its relationships.")
    return redirect('graph_list')

def delete_relationship(request, relationship_id):
    rel = get_object_or_404(GraphRelationship, id=relationship_id)
    
    # Delete from Neo4j
    try:
        if rel.relationship_id:
            conn = get_db_connection()
            conn.delete_relationship(int(rel.relationship_id))
            conn.close()
    except Exception as e:
        print(f"Error deleting Neo4j relationship: {e}")
    
    # Delete from Django
    rel_info = str(rel)
    rel.delete()
    
    messages.success(request, f"Relationship '{rel_info}' was successfully deleted.")
    return redirect('graph_list')

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
            if source.node_id and target.node_id:
                result = conn.create_relationship(
                    int(source.node_id), 
                    int(target.node_id), 
                    rel_type, 
                    properties
                )
                if result and result[0]['r'] is not None:
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
    # Get filter values
    node_label_filter = request.GET.get('node_label', '')
    rel_type_filter = request.GET.get('rel_type', '')
    
    # Apply filters
    nodes = GraphNode.objects.all()
    relationships = GraphRelationship.objects.all()
    
    if node_label_filter:
        nodes = nodes.filter(label=node_label_filter)
    
    if rel_type_filter:
        relationships = relationships.filter(type=rel_type_filter)
    
    # Get unique node labels and relationship types for filter dropdowns
    all_node_labels = GraphNode.objects.values_list('label', flat=True).distinct()
    all_rel_types = GraphRelationship.objects.values_list('type', flat=True).distinct()
    
    context = {
        'nodes': nodes,
        'relationships': relationships,
        'node_label_filter': node_label_filter,
        'rel_type_filter': rel_type_filter,
        'all_node_labels': all_node_labels,
        'all_rel_types': all_rel_types,
        'is_demo_mode': request.session.get('demo_mode', False)
    }
    
    return render(request, 'graphapp/graph_list.html', context)

def toggle_demo_mode(request):
    # Check the current state
    is_demo_mode = request.session.get('demo_mode', False)
    
    # Get the next page to redirect to
    next_page = request.GET.get('next', 'graph_list')
    
    # Toggle the state
    request.session['demo_mode'] = not is_demo_mode
    
    if not is_demo_mode:  # Turning demo mode ON
        # Backup existing data to session
        request.session['data_backup'] = {
            'nodes': list(GraphNode.objects.values()),
            'relationships': list(GraphRelationship.objects.values())
        }
        
        # Clear existing data
        GraphRelationship.objects.all().delete()
        GraphNode.objects.all().delete()
        
        # Try to create demo data in Neo4j, but continue if it fails
        try:
            conn = get_db_connection()
            conn.get_demo_data()
            conn.close()
        except Exception as e:
            print(f"Warning: Could not create Neo4j demo data: {e}")
            messages.warning(request, "Demo mode activated with local data only. Neo4j connection failed.")
        
        # Create corresponding Django models
        # Persons
        alice = GraphNode.objects.create(label="Person", name="Alice", 
                                        properties={"age": 32, "occupation": "Software Engineer"})
        bob = GraphNode.objects.create(label="Person", name="Bob", 
                                      properties={"age": 28, "occupation": "Data Scientist"})
        charlie = GraphNode.objects.create(label="Person", name="Charlie", 
                                          properties={"age": 35, "occupation": "Project Manager"})
        
        # Companies
        techcorp = GraphNode.objects.create(label="Company", name="TechCorp", 
                                           properties={"industry": "Technology", "founded": 2010})
        datainc = GraphNode.objects.create(label="Company", name="DataInc", 
                                         properties={"industry": "Data Analytics", "founded": 2015})
        
        # Skills
        python = GraphNode.objects.create(label="Skill", name="Python", 
                                         properties={"category": "Programming Language", "difficulty": "Intermediate"})
        ml = GraphNode.objects.create(label="Skill", name="Machine Learning", 
                                     properties={"category": "AI", "difficulty": "Advanced"})
        mgmt = GraphNode.objects.create(label="Skill", name="Management", 
                                      properties={"category": "Soft Skill", "difficulty": "Advanced"})
        
        # Relationships
        GraphRelationship.objects.create(source=alice, target=techcorp, type="WORKS_AT", 
                                        properties={"position": "Senior Developer", "since": 2018})
        GraphRelationship.objects.create(source=bob, target=datainc, type="WORKS_AT", 
                                        properties={"position": "Data Analyst", "since": 2019})
        GraphRelationship.objects.create(source=charlie, target=techcorp, type="WORKS_AT", 
                                        properties={"position": "Team Lead", "since": 2015})
        
        GraphRelationship.objects.create(source=alice, target=python, type="HAS_SKILL", 
                                        properties={"level": "Expert", "years": 5})
        GraphRelationship.objects.create(source=bob, target=python, type="HAS_SKILL", 
                                        properties={"level": "Proficient", "years": 3})
        GraphRelationship.objects.create(source=bob, target=ml, type="HAS_SKILL", 
                                        properties={"level": "Advanced", "years": 2})
        GraphRelationship.objects.create(source=charlie, target=mgmt, type="HAS_SKILL", 
                                        properties={"level": "Expert", "years": 8})
        
        GraphRelationship.objects.create(source=alice, target=bob, type="KNOWS", 
                                        properties={"since": 2017, "relationship": "Colleague"})
        GraphRelationship.objects.create(source=bob, target=charlie, type="KNOWS", 
                                        properties={"since": 2019, "relationship": "Manager"})
        
        if not request.session.get('neo4j_error', False):
            messages.success(request, "Demo mode activated. Showing sample data.")
    else:  # Turning demo mode OFF
        # Clear demo data
        GraphRelationship.objects.all().delete()
        GraphNode.objects.all().delete()
        
        # Try to reset Neo4j, but continue if it fails
        try:
            conn = get_db_connection()
            conn.run_query("MATCH (n) DETACH DELETE n")
            conn.close()
        except Exception as e:
            print(f"Warning: Could not reset Neo4j data: {e}")
        
        # Restore original data if it exists
        if 'data_backup' in request.session:
            # Restore nodes
            for node_data in request.session['data_backup']['nodes']:
                node = GraphNode.objects.create(
                    label=node_data['label'],
                    name=node_data['name'],
                    properties=node_data['properties'],
                    node_id=node_data['node_id']
                )
            
            # Restore relationships
            for rel_data in request.session['data_backup']['relationships']:
                source = GraphNode.objects.get(id=rel_data['source_id'])
                target = GraphNode.objects.get(id=rel_data['target_id'])
                GraphRelationship.objects.create(
                    source=source,
                    target=target,
                    type=rel_data['type'],
                    properties=rel_data['properties'],
                    relationship_id=rel_data['relationship_id']
                )
            
            # Clean up session storage
            del request.session['data_backup']
        
        messages.success(request, "Demo mode deactivated. Restored original data.")
    
    return redirect(next_page)

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
            'selected_relationship': relationship_filter,
            'all_node_labels': GraphNode.objects.values_list('label', flat=True).distinct(),
            'all_relationship_types': GraphRelationship.objects.values_list('type', flat=True).distinct(),
            'is_demo_mode': request.session.get('demo_mode', False)
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
        
        # Arrow head
        angle = calculate_angle(x0, y0, x1, y1)
        
        arrow_trace = go.Scatter(
            x=[xa, xa + 0.03 * np.cos(angle + np.pi/6), xa + 0.03 * np.cos(angle - np.pi/6), xa],
            y=[ya, ya + 0.03 * np.sin(angle + np.pi/6), ya + 0.03 * np.sin(angle - np.pi/6), ya],
            mode='lines',
            line=dict(width=2, color='#888'),
            fill='toself',
            hoverinfo='none',
            showlegend=False
        )
        edge_traces.append(arrow_trace)
    
    # Create nodes trace
    node_trace = go.Scatter(
        x=[pos[node][0] for node in G.nodes()],
        y=[pos[node][1] for node in G.nodes()],
        mode='markers+text',
        text=[G.nodes[node]['name'] for node in G.nodes()],
        textposition='bottom center',
        marker=dict(
            size=20,
            color=[G.nodes[node]['color'] for node in G.nodes()],
            line=dict(width=2, color='white')
        ),
        hoverinfo='text',
        hovertext=[G.nodes[node]['hover_text'] for node in G.nodes()],
        showlegend=False,
        hovertemplate='%{hovertext}<extra></extra>'
    )
    
    # Create figure
    fig = go.Figure(
        data=edge_traces + [node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode='closest',
            margin=dict(b=0, l=0, r=0, t=0),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            width=900,
            height=700,
            plot_bgcolor='white'
        )
    )
    
    # Add interactivity options
    fig.update_layout(
        autosize=True,
        dragmode='pan',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Open Sans"
        )
    )
    
    # Configure other interaction options
    fig.update_xaxes(range=[-1.2, 1.2], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(range=[-1.2, 1.2])
    
    # Convert to HTML
    graph_html = fig.to_html(
        full_html=False,
        include_plotlyjs='cdn',
        config={
            'displayModeBar': True,
            'scrollZoom': True,
            'modeBarButtonsToAdd': ['drawclosedpath', 'eraseshape']
        }
    )
    
    # Get all node labels and relationship types for filtering dropdowns
    all_node_labels = GraphNode.objects.values_list('label', flat=True).distinct()
    all_relationship_types = GraphRelationship.objects.values_list('type', flat=True).distinct()
    
    # Render template with graph
    return render(request, 'graphapp/visualize.html', {
        'graph_html': graph_html,
        'node_labels': label_colors,
        'relationship_types': rel_types,
        'selected_layout': layout_type,
        'selected_node_type': node_type_filter,
        'selected_relationship': relationship_filter,
        'all_node_labels': all_node_labels,
        'all_relationship_types': all_relationship_types,
        'is_demo_mode': request.session.get('demo_mode', False)
    })

def generate_distinct_colors(n):
    colors = []
    for i in range(n):
        hue = i / n
        saturation = 0.7
        value = 0.9
        rgb = colorsys.hsv_to_rgb(hue, saturation, value)
        hex_color = f"#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}"
        colors.append(hex_color)
    return colors

def calculate_angle(x0, y0, x1, y1):
    return np.arctan2(y1 - y0, x1 - x0) 