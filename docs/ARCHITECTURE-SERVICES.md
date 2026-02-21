# Service Component Details

This document provides detailed information about each service component in the TalkAI platform.

---

## Service Matrix

| Service | Port | Language | Framework | Dependencies |
|---------|------|----------|-----------|--------------|
| API Gateway | 8000 | Python | FastAPI | PostgreSQL, Redis |
| AI Router | 8001 | Python | FastAPI | Qdrant, Redis, LLM APIs |
| Action Engine | 8002 | Python | FastAPI | PostgreSQL, Redis, Vault |
| Policy Engine | 8003 | Python | FastAPI | PostgreSQL, Redis |
| Ingestion Service | 8004 | Python | FastAPI | PostgreSQL, Redis, K8s |
| Audit Service | 8005 | Python | FastAPI | PostgreSQL |
| Agent Service | 8006 | Python | FastAPI | PostgreSQL, Redis, K8s, AWS, Azure, GCP |
| Discovery Service | 8007 | Python | FastAPI | PostgreSQL |
| User Service | 8008 | Python | FastAPI | PostgreSQL, Redis |
| Monitoring Service | 8009 | Python | FastAPI | PostgreSQL, Redis, K8s |
| Cost Service | 8010 | Python | FastAPI | PostgreSQL, Redis |
| Onboarding Service | 8011 | Python | FastAPI | PostgreSQL, Vault |
| Workflow Service | 8012 | Python | FastAPI + Celery | PostgreSQL, Redis, NATS |
| Notification Service | 8013 | Python | FastAPI | PostgreSQL, Redis |
| Frontend | 3000 | TypeScript | React | API Gateway |

---

## Detailed Service Specifications

### 1. API Gateway (Port 8000)

**Location:** `services/api-gateway/`

**Files:**
- `main.py` - FastAPI application (38,017 chars)
- `auth.py` - Authentication middleware
- `scanner.py` - Request transformation
- `config.py` - Configuration
- `models.py` - Pydantic models

**Environment Variables:**
```
SERVICE_PORT=8000
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET=your-secret
```

**Key Endpoints:**
- `POST /api/v1/*` - Proxy to backend services
- `GET /health` - Health check
- `GET /api/v1/services` - List available services

---

### 2. AI Router (Port 8001)

**Location:** `services/ai-router/`

**Files:**
- `main.py` - FastAPI application
- `intent_classifier.py` - Query classification (16,682 chars)
- `query_pipeline.py` - Query processing
- `rag_engine.py` - RAG implementation
- `source_citations.py` - Source attribution
- `conversation_manager.py` - Chat history
- `approval_workflow.py` - Approval handling
- `llm_client.py` - LLM abstraction
- `models.py` - Data models

**Environment Variables:**
```
SERVICE_PORT=8001
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
QDRANT_URL=http://qdrant:6333
REDIS_URL=redis://...
```

**Key Endpoints:**
- `POST /ai/v1/chat` - Process chat message
- `POST /ai/v1/classify` - Classify intent
- `POST /ai/v1/rag/search` - RAG search
- `GET /ai/v1/conversations` - List conversations

---

### 3. Action Engine (Port 8002)

**Location:** `services/action-engine/`

**Files:**
- `main.py` - FastAPI application (14,942 chars)
- `executor.py` - Action execution (7,551 chars)
- `sandbox.py` - Dry-run simulation (11,266 chars)
- `rollback.py` - Rollback handling (8,574 chars)
- `models.py` - Action models

**Environment Variables:**
```
SERVICE_PORT=8002
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
VAULT_ADDR=http://vault:8200
```

**Key Endpoints:**
- `POST /api/v1/actions/execute` - Execute action
- `POST /api/v1/actions/dry-run` - Dry-run action
- `POST /api/v1/actions/rollback` - Rollback action

---

### 4. Policy Engine (Port 8003)

**Location:** `services/policy-engine/`

**Files:**
- `main.py` - FastAPI application (18,063 chars)
- `rbac.py` - RBAC implementation (7,750 chars)
- `approval_chain.py` - Approval workflows (5,228 chars)
- `models.py` - Policy models

**Environment Variables:**
```
SERVICE_PORT=8003
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

**Key Endpoints:**
- `POST /api/v1/policy/check` - Check permissions
- `POST /api/v1/policy/approve` - Approve action
- `GET /api/v1/policy/rules` - List rules

---

### 5. Ingestion Service (Port 8004)

**Location:** `services/ingestion-service/`

**Files:**
- `main.py` - FastAPI application
- `k8s_watcher.py` - K8s resource watching
- `cloud_collector.py` - Cloud data collection

**Environment Variables:**
```
SERVICE_PORT=8004
DATABASE_URL=postgresql://...
K8S_CONFIG_PATH=/path/to/config
```

**Key Endpoints:**
- `POST /api/v1/ingest/k8s` - Ingest K8s resources
- `POST /api/v1/ingest/cloud` - Ingest cloud resources

---

### 6. Audit Service (Port 8005)

**Location:** `services/audit-service/`

**Files:**
- `main.py` - FastAPI application (17,706 chars)
- `log_store.py` - Log storage (3,597 chars)
- `integrity.py` - Integrity verification (3,400 chars)
- `models.py` - Audit models (7,119 chars)

**Environment Variables:**
```
SERVICE_PORT=8005
DATABASE_URL=postgresql://...
```

**Key Endpoints:**
- `POST /api/v1/audit/log` - Create audit log
- `GET /api/v1/audit/logs` - Query audit logs
- `GET /api/v1/audit/export` - Export audit logs

---

### 7. Agent Service (Port 8006)

**Location:** `services/agent-service/`

**Files:**
- `app/main.py` - FastAPI application (31,249 chars)
- `app/agents/query_agent.py` - Query agent (11,745 chars)
- `app/agents/action_agent.py` - Action agent (29,592 chars)
- `app/agents/analysis_agent.py` - Analysis agent (36,497 chars)
- `app/agents/planning_agent.py` - Planning agent (24,833 chars)
- `app/agents/registry.py` - Agent registry (14,118 chars)
- `app/tools/k8s/read_tools.py` - K8s read tools (18,428 chars)
- `app/tools/k8s/write_tools.py` - K8s write tools (14,703 chars)
- `app/tools/k8s/exec_tools.py` - K8s exec tools (10,478 chars)
- `app/tools/k8s/multi_cluster.py` - Multi-cluster (8,974 chars)
- `app/tools/aws/ec2_tools.py` - AWS EC2 (9,985 chars)
- `app/tools/aws/s3_tools.py` - AWS S3 (7,531 chars)
- `app/tools/aws/eks_tools.py` - AWS EKS (7,281 chars)
- `app/tools/aws/cloudwatch_tools.py` - AWS CloudWatch (6,969 chars)
- `app/tools/azure/vm_tools.py` - Azure VMs (12,851 chars)
- `app/tools/azure/aks_tools.py` - Azure AKS (8,946 chars)
- `app/tools/azure/storage_tools.py` - Azure Storage (10,827 chars)
- `app/tools/gcp/gce_tools.py` - GCP GCE (11,405 chars)
- `app/tools/gcp/gke_tools.py` - GCP GKE (9,185 chars)
- `app/tools/gcp/storage_tools.py` - GCP Storage (5,870 chars)

**Environment Variables:**
```
SERVICE_PORT=8006
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
K8S_CONFIG_PATH=/path/to/config
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AZURE_SUBSCRIPTION_ID=...
GCP_PROJECT_ID=...
```

**Key Endpoints:**
- `POST /api/v1/agents/query` - Execute query
- `POST /api/v1/agents/action` - Execute action
- `POST /api/v1/agents/analyze` - Analyze infrastructure

---

### 8. Discovery Service (Port 8007)

**Location:** `services/discovery-service/`

**Files:**
- `main.py` - FastAPI application
- `scanner.py` - Network scanning

**Environment Variables:**
```
SERVICE_PORT=8007
DATABASE_URL=postgresql://...
```

**Key Endpoints:**
- `POST /api/v1/discovery/scan` - Start scan
- `GET /api/v1/discovery/hosts` - List discovered hosts

---

### 9. User Service (Port 8008)

**Location:** `services/user-service/`

**Files:**
- `main.py` - FastAPI application
- `config.py` - Configuration
- `models.py` - SQLAlchemy models
- `database.py` - Database setup
- `schemas.py` - Pydantic schemas
- `app/services/auth_service.py` - Authentication
- `app/services/user_service.py` - User CRUD
- `app/services/permission_service.py` - Permissions
- `app/api/v1/auth.py` - Auth endpoints
- `app/api/v1/users.py` - User endpoints
- `app/api/v1/permissions.py` - Permission endpoints

**Environment Variables:**
```
SERVICE_PORT=8008
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
JWT_SECRET=your-secret
OAUTH_GOOGLE_CLIENT_ID=...
OAUTH_GITHUB_CLIENT_ID=...
```

**Key Endpoints:**
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update user

---

### 10. Monitoring Service (Port 8009)

**Location:** `services/monitoring-service/`

**Files:**
- `app/main.py` - FastAPI application
- `app/config.py` - Configuration
- `app/models.py` - Monitoring models
- `app/services/self_healing.py` - Auto-remediation
- `app/services/proactive_insights.py` - AI insights
- `app/api/v1/health.py` - Health endpoints
- `app/api/v1/metrics.py` - Metrics endpoints
- `app/api/v1/self_healing.py` - Self-healing endpoints
- `app/api/v1/insights.py` - Insights endpoints

**Environment Variables:**
```
SERVICE_PORT=8009
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
K8S_CONFIG_PATH=/path/to/config
```

**Key Endpoints:**
- `GET /api/v1/monitoring/health` - Cluster health
- `GET /api/v1/monitoring/metrics` - Get metrics
- `GET /api/v1/monitoring/alerts` - List alerts
- `POST /api/v1/monitoring/self-healing/execute` - Execute remediation

---

### 11. Cost Service (Port 8010)

**Location:** `services/cost-service/`

**Files:**
- `main.py` - FastAPI application
- `config.py` - Configuration
- `app/models.py` - Cost models (20,198 chars)
- `app/schemas.py` - Pydantic schemas (18,884 chars)
- `app/services/estimator.py` - Cost estimation (20,658 chars)
- `app/services/optimizer.py` - Optimization (21,861 chars)
- `app/services/anomaly_detector.py` - Anomaly detection (26,279 chars)
- `app/services/collectors/aws_costs.py` - AWS collector
- `app/services/collectors/azure_costs.py` - Azure collector
- `app/services/collectors/gcp_costs.py` - GCP collector
- `app/services/collectors/kubernetes_costs.py` - K8s cost collector

**Environment Variables:**
```
SERVICE_PORT=8010
DATABASE_URL=postgresql://...
AWS_COST_EXPLORER_ROLE=...
AZURE_COST_MANAGEMENT=...
GCP_BILLING_ACCOUNT=...
```

**Key Endpoints:**
- `GET /api/v1/costs/daily` - Daily costs
- `GET /api/v1/costs/monthly` - Monthly costs
- `GET /api/v1/costs/budgets` - Budget status
- `GET /api/v1/costs/recommendations` - Optimization recommendations

---

### 12. Onboarding Service (Port 8011)

**Location:** `services/onboarding-service/`

**Files:**
- `main.py` - FastAPI application
- `config.py` - Configuration

**Environment Variables:**
```
SERVICE_PORT=8011
DATABASE_URL=postgresql://...
VAULT_ADDR=http://vault:8200
```

**Key Endpoints:**
- `POST /api/v1/clusters/register` - Register cluster
- `POST /api/v1/clusters/{id}/test` - Test connection
- `GET /api/v1/clusters` - List clusters

---

### 13. Workflow Service (Port 8012)

**Location:** `services/workflow-service/`

**Files:**
- `main.py` - FastAPI application (25,071 chars)
- `config.py` - Configuration
- `models.py` - Workflow models
- `tasks.py` - Celery tasks (14,806 chars)
- `step_handlers.py` - Step handlers (20,032 chars)
- `rollback.py` - Rollback engine (14,545 chars)
- `event_publisher.py` - NATS events (6,126 chars)
- `state_cache.py` - Redis state (4,939 chars)

**Environment Variables:**
```
SERVICE_PORT=8012
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
NATS_URL=nats://nats:4222
CELERY_BROKER_URL=redis://...
```

**Key Endpoints:**
- `POST /api/v1/workflows` - Create workflow
- `POST /api/v1/workflows/{id}/execute` - Execute workflow
- `GET /api/v1/workflows/{id}/status` - Get status
- `POST /api/v1/workflows/{id}/rollback` - Rollback

---

### 14. Notification Service (Port 8013)

**Location:** `services/notification-service/`

**Files:**
- `main.py` - FastAPI application
- `config.py` - Configuration
- `models.py` - Notification models
- `database.py` - Database setup
- `app/services/notification_sender.py` - Channel senders (14,188 chars)
- `app/api/v1/notifications.py` - Notification endpoints

**Environment Variables:**
```
SERVICE_PORT=8013
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SLACK_BOT_TOKEN=xoxb-...
TEAMS_WEBHOOK_URL=...
PAGERDUTY_API_KEY=...
```

**Key Endpoints:**
- `POST /api/v1/notifications/send` - Send notification
- `GET /api/v1/notifications` - List notifications
- `GET /api/v1/notifications/preferences/me` - Get preferences
- `PUT /api/v1/notifications/preferences/me` - Update preferences

---

### 15. Frontend (Port 3000)

**Location:** `services/frontend/`

**Tech Stack:**
- React 18
- TypeScript
- Vite
- TanStack Query
- Zustand
- Shadcn UI
- Tailwind CSS
- Socket.io Client

**Key Pages:**
- `/` - Dashboard
- `/infrastructure` - Infrastructure list
- `/discovered` - Discovered resources
- `/chat` - Chat interface
- `/workflows` - Workflow management
- `/monitoring` - Monitoring dashboard
- `/cost` - Cost management
- `/settings` - User settings
- `/welcome` - Onboarding wizard

**Environment Variables:**
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## Service Communication

### Synchronous (HTTP)
- API Gateway → All Services
- Frontend → API Gateway

### Asynchronous (NATS)
- Discovery → Ingestion
- Ingestion → RAG Service
- Workflow → Agent Service
- Monitoring → Notification Service

### Message Queue (Redis + Celery)
- Workflow Service task execution
- Background jobs
- Scheduled tasks

---

*Last Updated: 2026-02-16*
