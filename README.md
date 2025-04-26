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
   ELASTICSEARCH_CLOUD_ID=https://your-domain.es.us-east-1.aws.elastic.cloud:443
   ELASTICSEARCH_API_KEY=your_api_key
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

1. Ensure your `.env` is populated as described above.
2. Start the Flask app:
   ```bash
   # Option 1: using flask CLI
   export FLASK_APP=app.py
   export FLASK_ENV=development
   flask run

   # Option 2: directly
   python app.py
   ```
3. Open your browser at http://localhost:5000 to view, create, and edit incidents.