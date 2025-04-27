# LangGraph App

This application demonstrates how to connect to an Elasticsearch Serverless instance and use a simple graph storage implementation in Python.

## Setup
1. Create a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```env
   # Either your Elastic Cloud ID (recommended) or the full HTTPS URL of your Elasticsearch endpoint
# ELASTICSEARCH_CLOUD_ID: your Elastic Cloud ID or full Elasticsearch URL
ELASTICSEARCH_CLOUD_ID=<your_elasticsearch_cloud_id_or_url>
# ELASTICSEARCH_API_KEY: your Elasticsearch API key
ELASTICSEARCH_API_KEY=<your_api_key>
   # (Optional) Elasticsearch index name for incidents (default: 'incidents')
   ELASTICSEARCH_INDEX=incidents
# OpenTelemetry OTLP exporter configuration (optional)
# OTLP endpoint (e.g. your APM OTLP HTTP endpoint)
OTEL_EXPORTER_OTLP_ENDPOINT=<your_otlp_exporter_endpoint>
# OTLP headers, e.g. "Authorization=ApiKey <your_api_key>"
OTEL_EXPORTER_OTLP_HEADERS=<your_otlp_exporter_headers>
   # (Optional) Service name for OpenTelemetry (default: 'langcommander')
   OTEL_SERVICE_NAME=langcommander
   ```
4. Run the CLI:
   ```bash
   python main.py [command] [options]
   ```

## Commands

- create: Create a new incident.
  ```bash
  python main.py create -i <ID> -t <TITLE> -d <DESCRIPTION> -p <PRIORITY> [-a <ASSIGNED_TO>]
  ```
- view: View incident details by ID.
  ```bash
  python main.py view <ID>
  ```
- update: Update fields of an existing incident.
  ```bash
  python main.py update <ID> [-t <TITLE>] [-d <DESCRIPTION>] [-s <STATUS>] [-p <PRIORITY>] [-a <ASSIGNED_TO>]
  ```
- list: List recent incidents.
  ```bash
  python main.py list [-n <NUMBER>]
  ```
  
## Web UI

In addition to the CLI, you can run a Flask-based web UI to manage incidents via your browser.

1. Activate your Python virtual environment (if not already):
   ```bash
   source venv/bin/activate
   ```

2. Ensure your `.env` is populated as described above.
   (You can also add debug flags:)
   ```ini
   # Print spans to console
   OTEL_CONSOLE_EXPORTER=true
   # Enable debug-level logging for OpenTelemetry
   OTEL_DEBUG=true
   ```

3. Start the Flask app:
   ```bash
   # Option 1: using flask CLI
   export FLASK_APP=app.py
   export FLASK_ENV=development
   flask run

   # Option 2: directly
   python app.py
   ```

4. Open your browser at http://localhost:5000 to view, create, and edit incidents.
   - If port 5000 is in use, set a different port when starting:
     ```bash
     PORT=5001 python app.py
     # or with flask CLI:
     export FLASK_RUN_PORT=5001
     flask run
     ```

## Deploying to AWS Elastic Beanstalk

You can easily host this Flask app using AWS Elastic Beanstalk (Python platform).

1. Install and configure the EB CLI:
   ```bash
   pip install awsebcli
   eb init -p python-3.10 incident-commander
   ```
   When prompted, choose the default region and application name.

2. Create an environment and set environment variables in one step:
   ```bash
   eb create prod \
     --envvars \
       ELASTICSEARCH_CLOUD_ID=<your_cloud_id>,\
       ELASTICSEARCH_API_KEY=<your_api_key>,\
       OTEL_EXPORTER_OTLP_ENDPOINT=<otel_endpoint>,\
       OTEL_EXPORTER_OTLP_HEADERS=<otel_headers>\
       OTEL_CONSOLE_EXPORTER=false,\
       OTEL_DEBUG=false
   ```

3. Deploy updates:
   ```bash
   eb deploy
   ```

4. Open the live app:
   ```bash
   eb open
   ```

Your app will run with `gunicorn` (configured via the included `Procfile`) and respect the `$PORT` provided by Elastic Beanstalk.

## Elastic Alerts Webhook Integration

This application exposes an HTTP POST endpoint `/alerts` for receiving alert notifications from Elasticsearch (Watcher) or Kibana Alerting Connectors. When an alert fires, the app will create a new incident or update an existing one based on the alert ID.

### 1. Kibana Alerting (Webhook Connector)
1. In Kibana, navigate to **Stack Management → Rules and Connectors**.
2. Click **Create connector** and choose **Webhook**.
   - **Name**: My App Webhook
   - **URL**: `https://<YOUR_APP_DOMAIN>/alerts`
   - **Method**: `POST`
   - **Headers**:
     - `Content-Type: application/json`
   - (Optional) Add an `Authorization` header if you secure the endpoint.
3. In your Alert Rule, add an **Action** and select the webhook connector.
   - Use a JSON body template such as:
     ```json
     {
       "rule": {
         "id": "{{rule.id}}",
         "name": "{{rule.name}}",
         "severity": "{{rule.tags.severity}}"
       },
       "context": {{context}}
     }
     ```

### 2. Elasticsearch Watcher (Webhook Action)
If you use the Elasticsearch Watcher API directly, you can configure a webhook action in your watch:
```json
PUT _watcher/watch/incidents_watch
{
  "trigger": { "schedule": { "interval": "1h" } },
  "input": { /* your query or condition */ },
  "actions": {
    "notify_webhook": {
      "webhook": {
        "method": "POST",
        "host": ["<YOUR_APP_HOST>"],
        "port": 443,
        "path": "/alerts",
        "body": "{{ctx.payload}}",
        "headers": { "Content-Type": "application/json" }
      }
    }
  }
}
```

### 3. Testing the Webhook
You can simulate an alert notification with `curl`:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"rule":{"id":"123","name":"Test Alert","severity":"High"},"context":{}}' \
  https://<YOUR_APP_DOMAIN>/alerts -v
```
On success, the server responds with HTTP `204 No Content` and the incident is created/updated.