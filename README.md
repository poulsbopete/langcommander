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
   ELASTICSEARCH_CLOUD_ID=your_cloud_id
   ELASTICSEARCH_API_KEY_ID=your_api_key_id
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