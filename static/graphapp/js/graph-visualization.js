/**
 * Enhanced Graph Visualization JS
 * This file provides interactive features for the graph visualization
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if we have a graph to work with
    const graphContainer = document.querySelector('.graph-container');
    if (!graphContainer) return;
    
    // Make sure the overlay exists
    let overlay = document.querySelector('.graph-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'graph-overlay';
        overlay.innerHTML = '<div class="spinner"></div>';
        graphContainer.appendChild(overlay);
    }
    
    // Function to show/hide loading overlay
    function toggleLoading(show) {
        overlay.classList.toggle('active', show);
    }
    
    // Adjust the graph layout to match container size
    function resizeGraph() {
        const graphDiv = document.querySelector('.js-plotly-plot');
        if (graphDiv) {
            Plotly.relayout(graphDiv, {
                width: graphContainer.offsetWidth,
                height: 700
            });
        }
    }
    
    // Call resize on window resize
    window.addEventListener('resize', function() {
        resizeGraph();
    });
    
    // Initialize size on load
    resizeGraph();
    
    // Handle form submission
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function() {
            toggleLoading(true);
        });
    }
    
    // Handle node interactions
    const plotlyDiv = document.querySelector('.js-plotly-plot');
    if (plotlyDiv) {
        // Add highlighting for connected nodes on hover
        plotlyDiv.on('plotly_hover', function(data) {
            // Only process the first point (in case of multiple points)
            const point = data.points[0];
            
            // Check if we're hovering on a node (not an edge or label)
            if (point.marker && point.marker.size && point.customdata) {
                // Highlight this node
                point.marker.color = 'rgba(255, 207, 86, 1)'; // #FFCF56 with opacity
            }
        });
        
        // Handle click on nodes to show focused graph
        plotlyDiv.on('plotly_click', function(data) {
            const point = data.points[0];
            
            // Check if we're clicking on a node
            if (point.marker && point.marker.size) {
                // Get the node information from the DOM
                const nodeLabel = point.data.customdata ? point.data.customdata.split('<br>')[0].split(':')[1].trim() : '';
                
                // If we have a node type filter control, we can set it
                const nodeTypeFilter = document.getElementById('nodeTypeFilter');
                if (nodeTypeFilter && nodeLabel) {
                    // Show a tooltip indicating what filtering would do
                    const nodePosition = {
                        x: point.x,
                        y: point.y
                    };
                    
                    showTooltip(`Click to filter by ${nodeLabel} nodes`, nodePosition);
                }
            }
        });
    }
    
    // Simple tooltip function
    function showTooltip(message, position) {
        // Create or reuse tooltip element
        let tooltip = document.getElementById('graph-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'graph-tooltip';
            tooltip.style.position = 'absolute';
            tooltip.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
            tooltip.style.color = 'white';
            tooltip.style.padding = '5px 10px';
            tooltip.style.borderRadius = '3px';
            tooltip.style.pointerEvents = 'none';
            tooltip.style.zIndex = '1000';
            tooltip.style.fontSize = '12px';
            document.body.appendChild(tooltip);
        }
        
        // Position near the node
        const container = document.querySelector('.graph-container');
        const containerRect = container.getBoundingClientRect();
        
        // Convert from Plotly coordinates to screen coordinates
        const plotlyDiv = document.querySelector('.js-plotly-plot');
        const plotRect = plotlyDiv.getBoundingClientRect();
        
        // Very rough estimation - this would need to be adjusted based on actual scaling
        const x = plotRect.left + (position.x * plotRect.width / 2) + (plotRect.width / 2);
        const y = plotRect.top + (position.y * plotRect.height / 2) + (plotRect.height / 2);
        
        tooltip.style.left = x + 'px';
        tooltip.style.top = (y - 30) + 'px';
        tooltip.textContent = message;
        tooltip.style.display = 'block';
        
        // Hide after a delay
        setTimeout(function() {
            tooltip.style.display = 'none';
        }, 2000);
    }
    
    // Enable legend item click to filter
    const legendItems = document.querySelectorAll('.legend-item');
    legendItems.forEach(function(item) {
        item.style.cursor = 'pointer';
        
        item.addEventListener('click', function() {
            // Get the node type from the text
            const labelText = item.querySelector('span').textContent.trim();
            
            // Find if this is a node type or relationship
            const isNodeType = item.parentElement.querySelector('h6').textContent.includes('Node');
            
            // Set the appropriate filter
            if (isNodeType) {
                const nodeTypeFilter = document.getElementById('nodeTypeFilter');
                if (nodeTypeFilter) {
                    nodeTypeFilter.value = labelText;
                    // Submit the form
                    document.getElementById('filterForm').submit();
                }
            } else {
                const relationshipFilter = document.getElementById('relationshipFilter');
                if (relationshipFilter) {
                    relationshipFilter.value = labelText;
                    // Submit the form
                    document.getElementById('filterForm').submit();
                }
            }
        });
    });
}); 