// Neo4j Operations Logger
const Neo4jLogger = {
    // Store operations for this session
    operations: [],
    
    // Log successful operations
    logOperation: function(operation, timestamp) {
        const logMsg = `Neo4j Operation: ${operation} completed [${timestamp}]`;
        console.log(`%c${logMsg}`, 'color: green; font-weight: bold;');
        
        // Store operation
        this.operations.push({
            operation: operation,
            timestamp: timestamp,
            time: new Date().toISOString()
        });
    },
    
    // Initialize event listeners for Neo4j logs
    init: function() {
        console.log('Neo4j logger initialized and waiting for operations...');
        
        // Listen for Neo4j operations
        document.addEventListener('neo4j-operation', function(e) {
            Neo4jLogger.logOperation(e.detail.operation, e.detail.timestamp);
        });
    },
    
    // Show all operations this session
    showAllOperations: function() {
        if (this.operations.length === 0) {
            console.log('No Neo4j operations recorded in this session');
            return;
        }
        
        console.group('Neo4j Operations History');
        this.operations.forEach((op, index) => {
            console.log(`${index + 1}. ${op.operation} [${op.timestamp}]`);
        });
        console.groupEnd();
    }
};

// Initialize logger when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    Neo4jLogger.init();
}); 