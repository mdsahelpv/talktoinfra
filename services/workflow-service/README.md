# Workflow Service

Multi-step workflow engine for infrastructure automation.

## Features

- **Workflow Templates**: Pre-built templates for common operations
- **Step Types**: Action, Condition, Wait, Approval, Parallel, Notification
- **State Machine**: Full lifecycle management (draft → active → running → completed)
- **Rollback Support**: Automatic rollback on failure
- **Approval Chains**: Multi-level approval workflows
- **Event-Driven**: NATS integration for real-time updates

## API Endpoints

### Workflow Definitions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/workflows` | Create workflow |
| GET | `/api/v1/workflows` | List workflows |
| GET | `/api/v1/workflows/{id}` | Get workflow |
| PUT | `/api/v1/workflows/{id}` | Update workflow |
| DELETE | `/api/v1/workflows/{id}` | Delete workflow |

### Workflow Executions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/workflows/{id}/execute` | Start execution |
| GET | `/api/v1/executions` | List executions |
| GET | `/api/v1/executions/{id}` | Get execution details |
| POST | `/api/v1/executions/{id}/cancel` | Cancel execution |
| POST | `/api/v1/executions/{id}/rollback` | Rollback execution |

## Step Types

### ACTION
Execute an action (K8s deployment, Terraform apply, script, etc.)

```json
{
  "type": "action",
  "config": {
    "action": "kubectl_apply",
    "manifest": "k8s/deployment.yaml"
  }
}
```

### CONDITION
Conditional branching based on context

```json
{
  "type": "condition",
  "condition": "$.environment == 'production'",
  "condition_values": {"environment": "production"}
}
```

### WAIT
Wait for duration or event

```json
{
  "type": "wait",
  "config": {
    "duration_seconds": 60
  }
}
```

### APPROVAL
Require approval before proceeding

```json
{
  "type": "approval",
  "description": "Approve production deployment",
  "config": {
    "required_approvers": ["admin", "tech-lead"]
  }
}
```

### PARALLEL
Execute multiple steps in parallel

```json
{
  "type": "parallel",
  "parallel_steps": [...]
}
```

### NOTIFICATION
Send notification

```json
{
  "type": "notification",
  "config": {
    "channel": "slack",
    "message": "Deployment completed"
  }
}
```

## Pre-built Templates

### Kubernetes Deployment
Deploy to Kubernetes with health checks.

### Blue-Green Deployment
Zero-downtime deployment using blue-green strategy.

### Database Migration
Run database migration with automatic rollback on failure.

## Running the Service

```bash
# Install dependencies
cd services/workflow-service
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --port 8012

# Docker
docker build -t workflow-service .
docker run -p 8012:8012 workflow-service
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| WORKFLOW_SERVICE_PORT | Service port | 8012 |
| WORKFLOW_POSTGRES_URL | PostgreSQL connection | postgresql://... |
| WORKFLOW_REDIS_URL | Redis connection | redis://... |
| WORKFLOW_NATS_URL | NATS connection | nats://... |

## License

MIT
