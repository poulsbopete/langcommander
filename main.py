import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

class ElasticsearchGraph:
    def __init__(self, es_client, node_index="nodes", edge_index="edges"):
        self.es = es_client
        self.node_index = node_index
        self.edge_index = edge_index
        self._create_indices()

    def _create_indices(self):
        for index in [self.node_index, self.edge_index]:
            if not self.es.indices.exists(index=index):
                self.es.indices.create(index=index)

    def add_node(self, node_id, properties):
        body = properties.copy()
        body["node_id"] = node_id
        self.es.index(index=self.node_index, id=node_id, document=body)

    def get_node(self, node_id):
        try:
            return self.es.get(index=self.node_index, id=node_id)["_source"]
        except Exception:
            return None

    def add_edge(self, edge_id, source, target, properties):
        body = properties.copy()
        body["edge_id"] = edge_id
        body["source"] = source
        body["target"] = target
        self.es.index(index=self.edge_index, id=edge_id, document=body)

    def get_edge(self, edge_id):
        try:
            return self.es.get(index=self.edge_index, id=edge_id)["_source"]
        except Exception:
            return None

def main():
    load_dotenv()

    cloud_id = os.getenv("ELASTICSEARCH_CLOUD_ID")
    api_key_id = os.getenv("ELASTICSEARCH_API_KEY_ID")
    api_key = os.getenv("ELASTICSEARCH_API_KEY")

    if not all([cloud_id, api_key_id, api_key]):
        print("Please set ELASTICSEARCH_CLOUD_ID, ELASTICSEARCH_API_KEY_ID, and ELASTICSEARCH_API_KEY in .env")
        return

    es = Elasticsearch(
        cloud_id=cloud_id,
        api_key=(api_key_id, api_key)
    )

    graph = ElasticsearchGraph(es)

    # Example usage
    graph.add_node("1", {"name": "Node 1", "description": "This is node 1"})
    graph.add_node("2", {"name": "Node 2", "description": "This is node 2"})
    graph.add_edge("e1", "1", "2", {"relation": "knows"})

    node = graph.get_node("1")
    edge = graph.get_edge("e1")

    print("Node:", node)
    print("Edge:", edge)

if __name__ == "__main__":
    main()