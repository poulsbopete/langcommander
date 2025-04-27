import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import uuid
import telemetry
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
import openai
from main import ElasticsearchGraph, IncidentManager

# Load environment variables
load_dotenv()
# Configure OpenAI API key for embeddings (for semantic search / MCP)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Flask application
app = Flask(__name__)
# Make WSGI entrypoint for Elastic Beanstalk
application = app
# Instrument Flask app for tracing
telemetry.instrument_app(app)

# Secret key for session management (flash messages)
app.secret_key = os.getenv("SECRET_KEY", "devkey")

# Read Elasticsearch credentials
cloud_id = os.getenv("ELASTICSEARCH_CLOUD_ID")
api_key = os.getenv("ELASTICSEARCH_API_KEY")
if not cloud_id or not api_key:
    raise RuntimeError("Please set ELASTICSEARCH_CLOUD_ID and ELASTICSEARCH_API_KEY in .env")

# Initialize Elasticsearch client (support URL or Cloud ID)
# Initialize Elasticsearch client (support URL or Cloud ID)
if cloud_id.startswith("http://") or cloud_id.startswith("https://"):
    es = Elasticsearch(hosts=[cloud_id], api_key=api_key)
else:
    es = Elasticsearch(cloud_id=cloud_id, api_key=api_key)

# Instrument Elasticsearch client with OpenTelemetry tracing
telemetry.instrument_es()

## Initialize graph and incident manager
# Use a dedicated index for incidents (default: 'incidents')
incident_index = os.getenv("ELASTICSEARCH_INDEX", "incidents")
graph = ElasticsearchGraph(es, node_index=incident_index)
manager = IncidentManager(graph)

# ------------------------------------------------------------------
# Model Context Protocol (MCP) endpoint for semantic search
# ------------------------------------------------------------------
@app.route("/mcp", methods=["POST"])
def mcp_search():
    """Perform semantic search over incidents using embeddings (MCP)."""
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid JSON payload"}), 400
    query_text = payload.get("query") or payload.get("input")
    if not query_text:
        return jsonify({"error": "'query' field required"}), 400
    # choose embedding model (override via payload or env)
    model = payload.get("model") or os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    try:
        emb_resp = openai.Embedding.create(model=model, input=query_text)
        vector = emb_resp["data"][0]["embedding"]
    except Exception as e:
        app.logger.error(f"Embedding error: {e}")
        return jsonify({"error": "Embedding failed"}), 500
    # number of results
    try:
        k = int(payload.get("k", 10))
    except (TypeError, ValueError):
        k = 10
    # perform semantic search
    try:
        hits = manager.search_semantic(vector, k=k)
    except Exception as e:
        app.logger.error(f"Semantic search error: {e}")
        return jsonify({"error": "Search failed"}), 500
    return jsonify({"results": hits})

@app.route("/")
def index():
    incidents = manager.list_incidents(size=100)
    return render_template("list_incidents.html", incidents=incidents)

@app.route("/incidents/new", methods=["GET", "POST"])
def new_incident():
    if request.method == "POST":
        incident_id = request.form.get("id", "").strip()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority")
        assigned_to = request.form.get("assigned_to") or None

        if not incident_id or not title or not description:
            flash("ID, Title, and Description are required.", "danger")
            return render_template("incident_form.html", incident=request.form, form_action=url_for("new_incident"))

        if manager.get_incident(incident_id):
            flash(f"Incident {incident_id} already exists.", "danger")
            return render_template("incident_form.html", incident=request.form, form_action=url_for("new_incident"))

        manager.create_incident(incident_id, title, description, priority, assigned_to)
        flash(f"Incident {incident_id} created.", "success")
        return redirect(url_for("view_incident", incident_id=incident_id))

    return render_template("incident_form.html", incident={}, form_action=url_for("new_incident"))

@app.route("/incidents/<incident_id>")
def view_incident(incident_id):
    inc = manager.get_incident(incident_id)
    if not inc:
        flash(f"Incident {incident_id} not found.", "warning")
        return redirect(url_for("index"))
    return render_template("incident_detail.html", incident=inc)

@app.route("/incidents/<incident_id>/edit", methods=["GET", "POST"])
def edit_incident(incident_id):
    inc = manager.get_incident(incident_id)
    if not inc:
        flash(f"Incident {incident_id} not found.", "warning")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        status = request.form.get("status")
        priority = request.form.get("priority")
        assigned_to = request.form.get("assigned_to") or None

        manager.update_incident(
            incident_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
        )
        flash(f"Incident {incident_id} updated.", "success")
        return redirect(url_for("view_incident", incident_id=incident_id))

    return render_template("incident_form.html", incident=inc, form_action=url_for("edit_incident", incident_id=incident_id))

@app.route("/alerts", methods=["POST"])
def alerts_webhook():
    """Receive Elastic alert webhooks and create/update incidents."""
    payload = request.get_json(silent=True)
    if not payload:
        return "Invalid JSON payload", 400
    # Extract rule info or generate UUID
    rule = payload.get("rule", {})
    rule_id = rule.get("id") or str(uuid.uuid4())
    incident_id = f"alert-{rule_id}"
    title = rule.get("name", incident_id)
    description = json.dumps(payload)
    priority = rule.get("severity", "High")
    try:
        existing = manager.get_incident(incident_id)
        if existing:
            manager.update_incident(
                incident_id,
                description=description,
                status="Triggered",
                priority=priority,
            )
        else:
            manager.create_incident(
                incident_id,
                title,
                description,
                priority,
            )
        return "", 204
    except Exception as e:
        app.logger.error(f"Error handling alert webhook: {e}", exc_info=True)
        return "Internal error", 500

if __name__ == "__main__":
    # Allow overriding host and port via environment variables
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("FLASK_ENV", "").lower() == "development"
    app.run(debug=debug, host=host, port=port)