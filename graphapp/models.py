from django.db import models
from neo4j import GraphDatabase

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record for record in result]

    def create_node(self, label, properties):
        query = f"CREATE (n:{label} $props) RETURN n"
        return self.run_query(query, {"props": properties})

    def create_relationship(self, start_node_id, end_node_id, rel_type, properties=None):
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

    def get_all_nodes(self):
        query = "MATCH (n) RETURN n"
        return self.run_query(query)

    def get_all_relationships(self):
        query = "MATCH ()-[r]->() RETURN r"
        return self.run_query(query)

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