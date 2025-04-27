import os
import telemetry
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import argparse
import json
from datetime import datetime

class ElasticsearchGraph:
    def __init__(self, es_client, node_index="nodes", edge_index="edges"):
        self.es = es_client
        self.node_index = node_index
        self.edge_index = edge_index
        self._create_indices()

    def _create_indices(self):
        """
        Create node and edge indices. For the node index, include a dense_vector field for semantic search embeddings.
        """
        # dimensionality for embedding vectors (e.g. OpenAI ada-002 embeddings = 1536)
        dims = int(os.getenv("EMBEDDING_DIMS", "1536"))
        for index in [self.node_index, self.edge_index]:
            if not self.es.indices.exists(index=index):
                if index == self.node_index:
                    # create node index with embedding mapping
                    mapping = {
                        "mappings": {
                            "properties": {
                                # existing fields will be dynamic, add embedding for semantic search
                                "embedding": {"type": "dense_vector", "dims": dims}
                            }
                        }
                    }
                    self.es.indices.create(index=index, body=mapping)
                else:
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
    
    def update_node(self, node_id, properties):
        """
        Partially update a node's properties by ID.
        """
        self.es.update(index=self.node_index, id=node_id, doc=properties)

    def search_nodes(self, query=None, size=10):
        """
        Search nodes with an optional Elasticsearch query.
        """
        q = query if query is not None else {"match_all": {}}
        resp = self.es.search(index=self.node_index, query=q, size=size)
        return [hit["_source"] for hit in resp.get("hits", {}).get("hits", [])]
    
    def search_by_vector(self, vector, k=10):
        """
        Perform a kNN search on the embedding vector field.
        """
        body = {
            "size": k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": vector,
                        "k": k
                    }
                }
            }
        }
        resp = self.es.search(index=self.node_index, body=body)
        return [hit.get("_source", {}) for hit in resp.get("hits", {}).get("hits", [])]

class IncidentManager:
    """Manager for handling incident lifecycle using ElasticsearchGraph."""
    def __init__(self, graph):
        self.graph = graph

    def create_incident(self, incident_id, title, description, priority, assigned_to=None):
        props = {
            "type": "incident",
            "title": title,
            "description": description,
            "status": "New",
            "priority": priority,
            "assigned_to": assigned_to,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self.graph.add_node(incident_id, props)

    def get_incident(self, incident_id):
        incident = self.graph.get_node(incident_id)
        if incident and incident.get("type") == "incident":
            return incident
        return None

    def update_incident(self, incident_id, title=None, description=None, status=None, priority=None, assigned_to=None):
        fields = {}
        for field, value in [("title", title), ("description", description), ("status", status), ("priority", priority), ("assigned_to", assigned_to)]:
            if value is not None:
                fields[field] = value
        if not fields:
            return False
        fields["updated_at"] = datetime.utcnow().isoformat()
        self.graph.update_node(incident_id, fields)
        return True

    def list_incidents(self, size=10):
        # List all incidents ordered by created_at (not implemented sort yet)
        query = {"term": {"type": {"value": "incident"}}}
        return self.graph.search_nodes(query=query, size=size)
    
    def search_semantic(self, vector, k=10):
        """
        Semantic search for incidents using a vector via kNN.
        """
        return self.graph.search_by_vector(vector, k)

def _parse_args():
    parser = argparse.ArgumentParser(prog="incident_manager", description="Incident management CLI")
    sub = parser.add_subparsers(dest="command")

    # create
    pc = sub.add_parser("create", help="Create a new incident")
    pc.add_argument("-i", "--id", required=True, help="Incident ID")
    pc.add_argument("-t", "--title", required=True, help="Incident title")
    pc.add_argument("-d", "--description", required=True, help="Incident description")
    pc.add_argument("-p", "--priority", required=True, choices=["Low","Medium","High","Critical"], help="Priority level")
    pc.add_argument("-a", "--assigned_to", help="User assigned to")

    # view
    pv = sub.add_parser("view", help="View an incident details")
    pv.add_argument("id", help="Incident ID to view")

    # update
    pu = sub.add_parser("update", help="Update fields of an incident")
    pu.add_argument("id", help="Incident ID to update")
    pu.add_argument("-t", "--title", help="New title")
    pu.add_argument("-d", "--description", help="New description")
    pu.add_argument("-s", "--status", choices=["New","In Progress","Resolved","Closed"], help="New status")
    pu.add_argument("-p", "--priority", choices=["Low","Medium","High","Critical"], help="Priority level")
    pu.add_argument("-a", "--assigned_to", help="Reassign to user")

    # list
    pl = sub.add_parser("list", help="List incidents")
    pl.add_argument("-n", "--number", type=int, default=10, help="Number of incidents to list")

    return parser.parse_args()

def main():
    # parse CLI arguments early (handles -h/--help before ES setup)
    args = _parse_args()
    load_dotenv()

    cloud_id = os.getenv("ELASTICSEARCH_CLOUD_ID")
    api_key = os.getenv("ELASTICSEARCH_API_KEY")

    # Ensure required credentials are set
    if not all([cloud_id, api_key]):
        print("Please set ELASTICSEARCH_CLOUD_ID and ELASTICSEARCH_API_KEY in .env")
        return
    # Check for placeholder values
    placeholders = [cloud_id, api_key]
    if any(val.strip().startswith("your_") for val in placeholders):
        print("Please update .env with valid Elasticsearch credentials instead of placeholders.")
        return

    # Initialize Elasticsearch client, support both Cloud ID and direct URL
    try:
        if cloud_id.startswith("http://") or cloud_id.startswith("https://"):
            # Treat cloud_id as the Elasticsearch host URL
            es = Elasticsearch(
                hosts=[cloud_id],
                api_key=api_key
            )
        else:
            # Treat cloud_id as an Elastic Cloud ID
            es = Elasticsearch(
                cloud_id=cloud_id,
                api_key=api_key
            )
    except ValueError as e:
        print(f"Error initializing Elasticsearch client: {e}")
        return
    except Exception as e:
        print(f"Unexpected error creating Elasticsearch client: {e}")
        return

    # Instrument Elasticsearch client with OpenTelemetry
    telemetry.instrument_es()

    # Determine Elasticsearch index for incidents
    incident_index = os.getenv("ELASTICSEARCH_INDEX", "incidents")
    graph = ElasticsearchGraph(es, node_index=incident_index)
    manager = IncidentManager(graph)

    # Dispatch CLI commands
    if args.command == "create":
        manager.create_incident(
            args.id, args.title, args.description, args.priority, args.assigned_to
        )
        print(f"Incident {args.id} created.")
    elif args.command == "view":
        incident = manager.get_incident(args.id)
        if incident:
            print(json.dumps(incident, indent=2))
        else:
            print(f"Incident {args.id} not found.")
    elif args.command == "update":
        updated = manager.update_incident(
            args.id,
            title=args.title,
            description=args.description,
            status=args.status,
            priority=args.priority,
            assigned_to=args.assigned_to,
        )
        if updated:
            print(f"Incident {args.id} updated.")
        else:
            print(f"No updates applied to incident {args.id}.")
    elif args.command == "list":
        incidents = manager.list_incidents(size=args.number)
        for inc in incidents:
            print(json.dumps(inc, indent=2))
    else:
        print("No command specified. Use -h for help.")

if __name__ == "__main__":
    main()