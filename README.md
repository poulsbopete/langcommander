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
4. Run the app:
   ```bash
   python main.py
   ```