from django.db import models
from neo4j import GraphDatabase

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

    def run_query(self, query, parameters=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, ignoring query: {query}")
            return []
        
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record for record in result]

    def create_node(self, label, properties):
        if not self.connected:
            print(f"Warning: Neo4j not connected, ignoring node creation: {label}, {properties}")
            return [{"n": None}]
            
        query = f"CREATE (n:{label} $props) RETURN n"
        return self.run_query(query, {"props": properties})

    def create_relationship(self, start_node_id, end_node_id, rel_type, properties=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, ignoring relationship creation")
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
        return self.run_query(query, params)

    def delete_node(self, node_id):
        if not self.connected:
            print(f"Warning: Neo4j not connected, ignoring node deletion: {node_id}")
            return []
            
        # Delete the node and its relationships
        query = (
            "MATCH (n) "
            "WHERE id(n) = $node_id "
            "DETACH DELETE n"
        )
        return self.run_query(query, {"node_id": node_id})
        
    def delete_relationship(self, relationship_id):
        if not self.connected:
            print(f"Warning: Neo4j not connected, ignoring relationship deletion: {relationship_id}")
            return []
            
        # Delete just the relationship
        query = (
            "MATCH ()-[r]->() "
            "WHERE id(r) = $rel_id "
            "DELETE r"
        )
        return self.run_query(query, {"rel_id": relationship_id})

    def get_all_nodes(self):
        if not self.connected:
            print("Warning: Neo4j not connected, returning empty node list")
            return []
            
        query = "MATCH (n) RETURN n"
        return self.run_query(query)

    def get_all_relationships(self):
        if not self.connected:
            print("Warning: Neo4j not connected, returning empty relationship list")
            return []
            
        query = "MATCH ()-[r]->() RETURN r"
        return self.run_query(query)
        
    def get_filtered_nodes(self, label=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, returning empty node list for label: {label}")
            return []
            
        if label:
            query = f"MATCH (n:{label}) RETURN n"
            return self.run_query(query)
        else:
            return self.get_all_nodes()
            
    def get_filtered_relationships(self, rel_type=None):
        if not self.connected:
            print(f"Warning: Neo4j not connected, returning empty relationship list for type: {rel_type}")
            return []
            
        if rel_type:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN r"
            return self.run_query(query)
        else:
            return self.get_all_relationships()
            
    def get_demo_data(self):
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