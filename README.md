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
   ELASTICSEARCH_CLOUD_ID=Elastic serverless URL
   ELASTICSEARCH_API_KEY=Elastic API Key
   ELASTICSEARCH_INDEX=your index
   OTEL_EXPORTER_OTLP_ENDPOINT=Elastic O11Y Serverless URL
   OTEL_EXPORTER_OTLP_HEADERS=ApiKey ...
   OTEL_CONSOLE_EXPORTER=false
   OTEL_DEBUG=false
   OPENAI_API_KEY=Your OpenAI API key
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
   - Visit http://localhost:5000/chat to access the AI Chatbot interface.

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

## Deploying to AWS Fargate

You can also deploy this application as a containerized service on AWS Fargate. The following steps use the AWS CLI and Docker to build, push, and run your container.

### Prerequisites
- AWS CLI installed and configured with IAM permissions for ECR and ECS
- Docker installed locally
- An AWS account and default region set (`aws configure`)
- A VPC with public subnets and a security group allowing inbound traffic on your chosen port (e.g., 80 or 5000)

### 1. Create a Dockerfile
In the project root, add a file named `Dockerfile` with the following contents:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
ENV PORT=5000
CMD ["gunicorn", "app:application", "--bind", "0.0.0.0:5000", "--workers", "2"]
```

### 2. Build and Push to Amazon ECR
```bash
# Replace with your AWS account ID and region
ACCOUNT_ID=123456789012
REGION=us-west-2
REPO_NAME=langcommander

# 2.1 Create ECR repository (if it doesn't exist)
aws ecr create-repository --repository-name $REPO_NAME --region $REGION || true

# 2.2 Authenticate Docker to ECR
aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# 2.3 Build and tag the Docker image
docker build -t $REPO_NAME .
docker tag $REPO_NAME:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest

# 2.4 Push the image to ECR
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest
```

### 3. Create an ECS Cluster
```bash
CLUSTER_NAME=langcommander-cluster
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $REGION
```

### 4. Register a Fargate Task Definition
Create a file named `ecs-task-def.json`:
```json
{
  "family": "langcommander-task",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "networkMode": "awsvpc",
  "executionRoleArn": "arn:aws:iam::${ACCOUNT_ID}:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "langcommander",
      "image": "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:latest",
      "essential": true,
      "portMappings": [
        { "containerPort": 5000, "protocol": "tcp" }
      ],
      "environment": [
        { "name": "ELASTICSEARCH_CLOUD_ID", "value": "<your_cloud_id>" },
        { "name": "ELASTICSEARCH_API_KEY", "value": "<your_api_key>" },
        { "name": "ELASTICSEARCH_INDEX", "value": "langcommander" },
        { "name": "OPENAI_API_KEY",       "value": "<your_openai_key>" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/langcommander",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```
Register the task definition:
```bash
aws ecs register-task-definition \
  --cli-input-json file://ecs-task-def.json \
  --region $REGION
```

### 5. Deploy the Fargate Service
```bash
SERVICE_NAME=langcommander-service
SUBNET1=subnet-abc123
SUBNET2=subnet-def456
SECURITY_GROUP=sg-0123456789abcdef0

aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition langcommander-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET1,$SUBNET2],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --region $REGION
```

### 6. Access Your Service
The Fargate task will receive a public IP if `assignPublicIp` is enabled. Retrieve it:
```bash
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --region $REGION --query 'taskArns[0]' --output text)
ENI_ID=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN --region $REGION --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --region $REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text
```
You can then curl your app:
```bash
curl http://<PUBLIC_IP>:5000
```

### Cleanup
```bash
aws ecs delete-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force --region $REGION
aws ecs deregister-task-definition --task-definition langcommander-task --region $REGION
aws ecs delete-cluster --cluster $CLUSTER_NAME --region $REGION
aws ecr delete-repository --repository-name $REPO_NAME --force --region $REGION
```

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
  
## Semantic Search (MCP)

This application now supports semantic search over incidents via a Model Context Protocol (MCP) endpoint. It uses OpenAI embeddings and Elasticsearch k-NN vector search.

### Requirements
- Elasticsearch 8.x with Vector Search enabled
- OpenAI API Key (set `OPENAI_API_KEY` in your `.env`)
- (Optional) Override embedding model with `EMBEDDING_MODEL` (default: `text-embedding-ada-002`)
- (Optional) Override embedding dimensions with `EMBEDDING_DIMS` (default: `1536`)

### Endpoint
POST `/mcp`

Request JSON fields:
- `query` (or `input`): the text to semantic-search
- `model`: override the embedding model (optional)
- `k`: number of top results to return (optional, default: 10)

Response JSON:
```json
{
  "results": [
    { /* incident document */ },
    ...
  ]
}
```

### Example usage
```bash
curl -X POST http://localhost:5000/mcp \
  -H "Content-Type: application/json" \
  -d '{"query":"database outage","k":5}'
```
On success, the server responds with HTTP `204 No Content` and the incident is created/updated.