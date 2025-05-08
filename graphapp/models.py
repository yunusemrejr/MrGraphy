from django.db import models
from neo4j import GraphDatabase
import json
from django.http import JsonResponse
from datetime import datetime

class Neo4jConnection:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test the connection - this will raise an exception if connection fails
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.connected = True
        except Exception as e:
            print(f"Warning: Could not connect to Neo4j: {e}")
            self.connected = False

    def close(self):
        if hasattr(self, 'driver') and self.connected:
            self.driver.close()

    # Helper method to log successful Neo4j operations
    def log_operation(self, request, operation):
        if request and self.connected:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_data = {
                'operation': operation,
                'timestamp': timestamp
            }
            request.session['neo4j_log'] = json.dumps(log_data)
            return True
        return False
        
    # Helper method to track Neo4j operation failures
    def track_failure(self, request, operation, details=None):
        if request:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            failure_data = {
                'operation': operation,
                'timestamp': timestamp,
                'details': details or "Neo4j connection failed or operation not completed"
            }
            request.session['neo4j_failure'] = json.dumps(failure_data)
            request.session['neo4j_connected'] = False
            return True
        return False

    def run_query(self, query, parameters=None, request=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, ignoring query: {query}")
            if request:
                self.track_failure(request, "Query failed", "Neo4j database not connected")
            return []
        
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            data = [record for record in result]
            
            # Log successful operation if request is provided
            if request and data:
                self.log_operation(request, "Query executed")
                request.session['neo4j_connected'] = True
                
            return data

    def create_node(self, label, properties, request=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, ignoring node creation: {label}, {properties}")
            if request:
                node_name = properties.get('name', 'Unknown')
                self.track_failure(request, f"Node creation failed: {label} {node_name}", 
                                  "Neo4j database not connected")
            return [{"n": None}]
            
        query = f"CREATE (n:{label} $props) RETURN n"
        result = self.run_query(query, {"props": properties})
        
        # Log successful operation if request is provided
        if request:
            if result and result[0].get("n"):
                node_name = properties.get('name', 'Unknown')
                self.log_operation(request, f"Created {label} node: {node_name}")
                request.session['neo4j_connected'] = True
            else:
                node_name = properties.get('name', 'Unknown') 
                self.track_failure(request, f"Node creation failed: {label} {node_name}",
                                 "Operation completed but node not returned")
            
        return result

    def create_relationship(self, start_node_id, end_node_id, rel_type, properties=None, request=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, ignoring relationship creation")
            if request:
                self.track_failure(request, f"Relationship creation failed: {rel_type}", 
                                  "Neo4j database not connected")
            return [{"r": None}]
            
        query = (
            f"MATCH (a), (b) "
            f"WHERE id(a) = $start_id AND id(b) = $end_id "
            f"CREATE (a)-[r:{rel_type} $props]->(b) "
            f"RETURN r"
        )
        params = {
            "start_id": start_node_id,
            "end_id": end_node_id,
            "props": properties or {}
        }
        result = self.run_query(query, params)
        
        # Log successful operation if request is provided
        if request:
            if result and result[0].get("r"):
                self.log_operation(request, f"Created relationship: {rel_type}")
                request.session['neo4j_connected'] = True
            else:
                self.track_failure(request, f"Relationship creation failed: {rel_type}",
                                 "Operation completed but relationship not returned")
            
        return result

    def delete_node(self, node_id, request=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, ignoring node deletion: {node_id}")
            if request:
                self.track_failure(request, f"Node deletion failed: ID {node_id}", 
                                  "Neo4j database not connected")
            return []
            
        # Get node info before deletion
        node_info = "unknown"
        if self.connected:
            query = "MATCH (n) WHERE id(n) = $node_id RETURN n.name, labels(n) as labels"
            info_result = self.run_query(query, {"node_id": node_id})
            if info_result and len(info_result) > 0:
                node_name = info_result[0].get("n.name", "Unknown")
                node_labels = info_result[0].get("labels", [])
                if node_labels and len(node_labels) > 0:
                    node_info = f"{node_labels[0]}:{node_name}"
                else:
                    node_info = node_name
            
        # Delete the node and its relationships
        query = (
            "MATCH (n) "
            "WHERE id(n) = $node_id "
            "DETACH DELETE n"
        )
        result = self.run_query(query, {"node_id": node_id})
        
        # Log successful operation if request is provided
        if request:
            if self.connected and result is not None:
                self.log_operation(request, f"Deleted node: {node_info}")
                request.session['neo4j_connected'] = True
            else:
                self.track_failure(request, f"Node deletion failed: {node_info}",
                                 "Operation may not have completed successfully")
            
        return result
        
    def delete_relationship(self, relationship_id, request=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, ignoring relationship deletion: {relationship_id}")
            if request:
                self.track_failure(request, f"Relationship deletion failed: ID {relationship_id}", 
                                  "Neo4j database not connected")
            return []
            
        # Get relationship info before deletion
        rel_info = "unknown"
        if self.connected:
            query = "MATCH ()-[r]->() WHERE id(r) = $rel_id RETURN type(r) as type"
            info_result = self.run_query(query, {"rel_id": relationship_id})
            if info_result and len(info_result) > 0:
                rel_info = info_result[0].get("type", "unknown")
            
        # Delete just the relationship
        query = (
            "MATCH ()-[r]->() "
            "WHERE id(r) = $rel_id "
            "DELETE r"
        )
        result = self.run_query(query, {"rel_id": relationship_id})
        
        # Log successful operation if request is provided
        if request:
            if self.connected and result is not None:
                self.log_operation(request, f"Deleted relationship: {rel_info}")
                request.session['neo4j_connected'] = True
            else:
                self.track_failure(request, f"Relationship deletion failed: {rel_info}",
                                 "Operation may not have completed successfully")
            
        return result

    def get_all_nodes(self, request=None):
        if not self.connected:
            print("Warning: Neo4j not connected, returning empty node list")
            return []
            
        query = "MATCH (n) RETURN n"
        result = self.run_query(query)
        
        # Log successful operation if request is provided
        if request and result:
            node_count = len(result)
            self.log_operation(request, f"Retrieved all nodes ({node_count} found)")
            
        return result

    def get_all_relationships(self, request=None):
        if not self.connected:
            print("Warning: Neo4j not connected, returning empty relationship list")
            return []
            
        query = "MATCH ()-[r]->() RETURN r"
        result = self.run_query(query)
        
        # Log successful operation if request is provided
        if request and result:
            rel_count = len(result)
            self.log_operation(request, f"Retrieved all relationships ({rel_count} found)")
            
        return result
        
    def get_filtered_nodes(self, label=None, request=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, returning empty node list for label: {label}")
            return []
            
        if label:
            query = f"MATCH (n:{label}) RETURN n"
            result = self.run_query(query)
            
            # Log successful operation if request is provided
            if request and result:
                node_count = len(result)
                self.log_operation(request, f"Retrieved {label} nodes ({node_count} found)")
                
            return result
        else:
            return self.get_all_nodes(request)
            
    def get_filtered_relationships(self, rel_type=None, request=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, returning empty relationship list for type: {rel_type}")
            return []
            
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN r"
            result = self.run_query(query)
            
            # Log successful operation if request is provided
            if request and result:
                rel_count = len(result)
                self.log_operation(request, f"Retrieved {rel_type} relationships ({rel_count} found)")
                
            return result
        else:
            return self.get_all_relationships(request)
            
    def get_demo_data(self, request=None):
        if not self.connected:
            print("Warning: Neo4j not connected, skipping demo data creation")
            return "Demo data could not be created in Neo4j, connection failed"
        
        # Clear existing data
        self.run_query("MATCH (n) DETACH DELETE n")
        
        # Create demo nodes
        queries = [
            "CREATE (p:Person {name: 'Alice', age: 32, occupation: 'Software Engineer'})",
            "CREATE (p:Person {name: 'Bob', age: 28, occupation: 'Data Scientist'})",
            "CREATE (p:Person {name: 'Charlie', age: 35, occupation: 'Project Manager'})",
            "CREATE (c:Company {name: 'TechCorp', industry: 'Technology', founded: 2010})",
            "CREATE (c:Company {name: 'DataInc', industry: 'Data Analytics', founded: 2015})",
            "CREATE (s:Skill {name: 'Python', category: 'Programming Language', difficulty: 'Intermediate'})",
            "CREATE (s:Skill {name: 'Machine Learning', category: 'AI', difficulty: 'Advanced'})",
            "CREATE (s:Skill {name: 'Management', category: 'Soft Skill', difficulty: 'Advanced'})"
        ]
        
        for query in queries:
            self.run_query(query)
            
        # Create relationships
        rel_queries = [
            "MATCH (a:Person {name: 'Alice'}), (c:Company {name: 'TechCorp'}) CREATE (a)-[:WORKS_AT {position: 'Senior Developer', since: 2018}]->(c)",
            "MATCH (b:Person {name: 'Bob'}), (c:Company {name: 'DataInc'}) CREATE (b)-[:WORKS_AT {position: 'Data Analyst', since: 2019}]->(c)",
            "MATCH (c:Person {name: 'Charlie'}), (co:Company {name: 'TechCorp'}) CREATE (c)-[:WORKS_AT {position: 'Team Lead', since: 2015}]->(co)",
            "MATCH (a:Person {name: 'Alice'}), (s:Skill {name: 'Python'}) CREATE (a)-[:HAS_SKILL {level: 'Expert', years: 5}]->(s)",
            "MATCH (b:Person {name: 'Bob'}), (s:Skill {name: 'Python'}) CREATE (b)-[:HAS_SKILL {level: 'Proficient', years: 3}]->(s)",
            "MATCH (b:Person {name: 'Bob'}), (s:Skill {name: 'Machine Learning'}) CREATE (b)-[:HAS_SKILL {level: 'Advanced', years: 2}]->(s)",
            "MATCH (c:Person {name: 'Charlie'}), (s:Skill {name: 'Management'}) CREATE (c)-[:HAS_SKILL {level: 'Expert', years: 8}]->(s)",
            "MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'}) CREATE (a)-[:KNOWS {since: 2017, relationship: 'Colleague'}]->(b)",
            "MATCH (b:Person {name: 'Bob'}), (c:Person {name: 'Charlie'}) CREATE (b)-[:KNOWS {since: 2019, relationship: 'Manager'}]->(c)"
        ]
        
        for query in rel_queries:
            self.run_query(query)
            
        # Log successful operation if request is provided
        if request:
            self.log_operation(request, "Created complete demo dataset (8 nodes, 9 relationships)")
            
        return "Demo data created successfully"

class GraphNode(models.Model):
    label = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    properties = models.JSONField(default=dict)
    node_id = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"{self.label}: {self.name}"

class GraphRelationship(models.Model):
    source = models.ForeignKey(GraphNode, related_name='outgoing_relationships', on_delete=models.CASCADE)
    target = models.ForeignKey(GraphNode, related_name='incoming_relationships', on_delete=models.CASCADE)
    type = models.CharField(max_length=100)
    properties = models.JSONField(default=dict)
    relationship_id = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"{self.source.name} --[{self.type}]--> {self.target.name}" 