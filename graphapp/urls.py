from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('add-node/', views.add_node, name='add_node'),
    path('add-relationship/', views.add_relationship, name='add_relationship'),
    path('graph-list/', views.graph_list, name='graph_list'),
    path('visualize/', views.visualize_graph, name='visualize'),
] 