// Neo4j Operations Logger
const Neo4jLogger = {
    // Log successful operations
    logOperation: function(operation, timestamp) {
        console.log(`Neo4j Operation: ${operation} completed [${timestamp}]`);
    },
    
    // Initialize event listeners for Neo4j logs
    init: function() {
        document.addEventListener('neo4j-operation', function(e) {
            Neo4jLogger.logOperation(e.detail.operation, e.detail.timestamp);
        });
        console.log('Neo4j logger initialized');
    }
};

// Initialize logger when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    Neo4jLogger.init();
}); 