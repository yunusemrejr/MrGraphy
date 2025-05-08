from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('add-node/', views.add_node, name='add_node'),
    path('add-relationship/', views.add_relationship, name='add_relationship'),
    path('graph-list/', views.graph_list, name='graph_list'),
    path('visualize/', views.visualize_graph, name='visualize'),
    path('delete-node/<int:node_id>/', views.delete_node, name='delete_node'),
    path('delete-relationship/<int:relationship_id>/', views.delete_relationship, name='delete_relationship'),
    path('toggle-demo-mode/', views.toggle_demo_mode, name='toggle_demo_mode'),
    path('reset-neo4j-status/', views.reset_neo4j_status, name='reset_neo4j_status'),
] 