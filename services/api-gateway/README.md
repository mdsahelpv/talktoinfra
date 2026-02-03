# API Gateway Service

Entry point for all client requests to the AI Infrastructure Operations Platform.

## Responsibilities

- **Authentication**: JWT-based auth with role verification
- **Rate Limiting**: Configurable limits per endpoint
- **Request Routing**: Proxies requests to backend services
- **WebSocket**: Real-time chat interface
- **Metrics**: Prometheus metrics collection
- **Audit**: Logs all requests for compliance

## Endpoints

### Health & Metrics
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### Authentication
- `POST /auth/login` - User login
- `POST /auth/refresh` - Token refresh

### Queries
- `POST /api/v1/query` - Submit natural language query

### Actions
- `POST /api/v1/actions/dry-run` - Execute dry-run
- `POST /api/v1/actions/execute` - Execute approved action

### Approvals
- `GET /api/v1/approvals/pending` - List pending approvals
- `POST /api/v1/approvals/{id}/approve` - Approve action
- `POST /api/v1/approvals/{id}/reject` - Reject action

### WebSocket
- `WS /ws/chat/{conversation_id}` - Real-time chat

## Configuration

Environment variables:
- `SERVICE_PORT` - Port to listen on (default: 8000)
- `JWT_SECRET` - Secret for JWT signing
- `POSTGRES_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `AI_ROUTER_URL` - AI Router service URL
- `ACTION_ENGINE_URL` - Action Engine service URL
- `POLICY_ENGINE_URL` - Policy Engine service URL
- `AUDIT_SERVICE_URL` - Audit Service URL

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --port 8000

# Run with Docker
docker build -t opsai-api-gateway .
docker run -p 8000:8000 opsai-api-gateway
```
