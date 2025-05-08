/**
 * Enhanced Graph Visualization JS
 * This file provides interactive features for the graph visualization
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if we have a graph to work with
    const graphContainer = document.querySelector('.graph-container');
    if (!graphContainer) return;
    
    // Add loading overlay to graph container
    const overlay = document.createElement('div');
    overlay.className = 'graph-overlay';
    overlay.innerHTML = '<div class="spinner"></div>';
    graphContainer.appendChild(overlay);
    
    // Function to show/hide loading overlay
    function toggleLoading(show) {
        overlay.classList.toggle('active', show);
    }
    
    // Functionality for filtering nodes by type
    const nodeTypeFilter = document.getElementById('nodeTypeFilter');
    if (nodeTypeFilter) {
        nodeTypeFilter.addEventListener('change', function() {
            // This would be implemented in a future version with backend support
            console.log('Node type filtering will be implemented in a future version');
        });
    }
    
    // Functionality for filtering relationships by type
    const relationshipFilter = document.getElementById('relationshipFilter');
    if (relationshipFilter) {
        relationshipFilter.addEventListener('change', function() {
            // This would be implemented in a future version with backend support
            console.log('Relationship filtering will be implemented in a future version');
        });
    }
    
    // Functionality for changing layout algorithm
    const layoutType = document.getElementById('layoutType');
    if (layoutType) {
        layoutType.addEventListener('change', function() {
            // This would be implemented in a future version with backend support
            console.log('Layout algorithm change will be implemented in a future version');
        });
    }
    
    // Add click handler to graph nodes
    const plotlyDiv = document.querySelector('.js-plotly-plot');
    if (plotlyDiv) {
        plotlyDiv.on('plotly_click', function(data) {
            // Handle node click - could show detailed info or highlight connections
            console.log('Node clicked:', data);
        });
        
        // Add hover effect to nodes
        plotlyDiv.on('plotly_hover', function(data) {
            // We could enhance hover effects here
            console.log('Node hovered:', data);
        });
    }
}); 