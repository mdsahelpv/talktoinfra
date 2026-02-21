# TalkAI Platform - Complete Architecture

## Overview

TalkAI is an AI-powered infrastructure management platform that enables users to interact with their Kubernetes clusters, cloud resources, and discovered infrastructure through natural language queries and automated workflows.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FRONTEND (Port 3000)                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   React     │  │   Zustand   │  │   TanStack  │  │    Shadcn   │  │   Socket.io │  │
│  │   App       │  │   Stores    │  │   Query     │  │     UI      │  │   Client    │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               API GATEWAY (Port 8000)                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   Auth      │  │   Rate      │  │   Request   │  │   Response  │  │   WebSocket │  │
│  │   Middleware│  │   Limiter   │  │   Router    │  │   Transformer│ │   Handler   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
        ┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼              ▼              ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  AI Router    │ │ Agent Service │ │   Discovery   │ │  Onboarding   │ │    User       │
│  (Port 8001)  │ │  (Port 8006)  │ │  (Port 8007)  │ │  (Port 8011)  │ │  (Port 8008)  │
├───────────────┤ ├───────────────┤ ├───────────────┤ ├───────────────┤ ├───────────────┤
│ Intent        │ │ Query Agent   │ │ Port Scanner  │ │ Kubeconfig    │ │ JWT Auth      │
│ Classifier    │ │ Action Agent  │ │ Service       │ │ Validator     │ │ OAuth2/OIDC   │
│ Query Pipeline│ │ Analysis      │ │ Discovery     │ │ Cluster       │ │ MFA/TOTP      │
│ RAG Engine    │ │ Planning      │ │ Scanner       │ │ Onboarding    │ │ RBAC          │
│ Source        │ │ Tools         │ │ Nmap/Masscan  │ │ Connection    │ │ Teams         │
│ Citations     │ │ Registry      │ │               │ │ Tester        │ │ Permissions   │
└───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘
        │              │              │              │              │
        └──────────────┴──────────────┴──────────────┴──────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              CORE SERVICES                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Action     │  │   Policy    │  │   Audit     │  │  Ingestion  │  │ Monitoring  │  │
│  │  Engine     │  │   Engine    │  │   Service   │  │   Service   │  │  Service    │  │
│  │  (8002)     │  │   (8003)    │  │   (8005)    │  │   (8004)    │  │  (8009)     │  │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤  │
│  │ Executor    │  │ RBAC        │  │ Log Store   │  │ K8s Watcher │  │ Health      │  │
│  │ Sandbox     │  │ Approval    │  │ Integrity   │  │ Cloud       │  │ Metrics     │  │
│  │ Rollback    │  │ Chain       │  │ Compliance  │  │ Collector   │  │ Alerts      │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │
│                                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │
│  │    Cost     │  │   Workflow  │  │    RAG      │  │ Notification│                   │
│  │   Service   │  │   Service   │  │   Service   │  │  Service    │                   │
│  │  (8010)     │  │  (8012)     │  │  (Port ?)   │  │  (8013)     │                   │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤                   │
│  │ Cost        │  │ Celery      │  │ Qdrant      │  │ Email       │                   │
│  │ Explorer    │  │ Tasks       │  │ Indexer     │  │ Slack       │                   │
│  │ Optimizer   │  │ Step        │  │ Embedder    │  │ Teams       │                   │
│  │ Estimator   │  │ Handlers    │  │ Pipeline    │  │ PagerDuty   │                   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              INFRASTRUCTURE                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │
│  │ PostgreSQL  │  │   Redis     │  │   Qdrant    │  │    NATS     │                   │
│  │   :5432     │  │   :6379     │  │   :6333     │  │   :4222     │                   │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤                   │
│  │ User Data   │  │ Sessions    │  │ Vector      │  │ Event Bus   │                   │
│  │ Discovery   │  │ Cache       │  │ Search      │  │ Pub/Sub     │                   │
│  │ Workflows   │  │ Celery      │  │ Embeddings  │  │ Streaming   │                   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL INTEGRATIONS                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Kubernetes  │  │     AWS     │  │    Azure    │  │     GCP     │  │   LLM       │  │
│  │   Clusters  │  │  (EC2,S3,   │  │  (VM, AKS,  │  │  (GCE, GKE, │  │  Providers  │  │
│  │             │  │   EKS, CW)  │  │   Storage)  │  │   Storage)  │  │ (OpenAI,    │  │
│  │             │  │             │  │             │  │             │  │  Anthropic) │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Service Catalog

### 1. API Gateway (Port 8000)
**Purpose:** Entry point for all client requests

**Components:**
- `auth.py` - JWT token validation
- `scanner.py` - Request/response transformation
- `main.py` - FastAPI application with routing

**Responsibilities:**
- Authentication & authorization
- Rate limiting
- Request routing to backend services
- WebSocket handling for real-time updates

---

### 2. AI Router (Port 8001)
**Purpose:** Natural language processing and intent classification

**Components:**
- `intent_classifier.py` - Classifies user queries (read/action/analysis/planning)
- `query_pipeline.py` - Query processing pipeline
- `rag_engine.py` - Retrieval-augmented generation
- `source_citations.py` - Source attribution for AI responses
- `conversation_manager.py` - Chat history management
- `approval_workflow.py` - Approval request handling

**Responsibilities:**
- Intent classification and routing
- RAG-based query answering
- Source citations and traceability
- Conversation context management

---

### 3. Action Engine (Port 8002)
**Purpose:** Execute infrastructure changes safely

**Components:**
- `executor.py` - Action execution engine
- `sandbox.py` - Dry-run and simulation
- `rollback.py` - Automatic rollback on failure

**Responsibilities:**
- Execute approved actions
- Dry-run validation
- Rollback on failure
- Execution history tracking

---

### 4. Policy Engine (Port 8003)
**Purpose:** Safety checks and approval workflows

**Components:**
- `rbac.py` - Role-based access control
- `approval_chain.py` - Multi-level approval workflows
- `models.py` - Policy and rule definitions

**Responsibilities:**
- Permission checking
- Approval workflow orchestration
- Safety policy enforcement

---

### 5. Ingestion Service (Port 8004)
**Purpose:** Collect and process infrastructure data

**Components:**
- `k8s_watcher.py` - Kubernetes resource watching
- `cloud_collector.py` - Cloud provider data collection
- `processors/` - Data transformation pipelines

**Responsibilities:**
- K8s resource synchronization
- Cloud resource discovery
- Data normalization and enrichment

---

### 6. Audit Service (Port 8005)
**Purpose:** Comprehensive audit logging

**Components:**
- `log_store.py` - Audit log storage
- `integrity.py` - Log integrity verification
- `main.py` - Audit API endpoints

**Responsibilities:**
- Log all user actions
- Log all system events
- Compliance reporting
- Log integrity verification

---

### 7. Agent Service (Port 8006)
**Purpose:** Infrastructure tool execution

**Components:**
- `agents/query_agent.py` - Read-only queries
- `agents/action_agent.py` - Execute actions
- `agents/analysis_agent.py` - Analyze infrastructure
- `agents/planning_agent.py` - Create execution plans
- `tools/k8s/` - Kubernetes tools (read, write, exec)
- `tools/aws/` - AWS tools (EC2, S3, EKS, CloudWatch)
- `tools/azure/` - Azure tools (VM, AKS, Storage)
- `tools/gcp/` - GCP tools (GCE, GKE, Storage)
- `tools/registry.py` - Tool registration and discovery

**Responsibilities:**
- Execute infrastructure queries
- Perform infrastructure actions
- Multi-cluster support
- Tool validation

---

### 8. Discovery Service (Port 8007)
**Purpose:** Discover infrastructure through scanning

**Components:**
- `scanner.py` - Network scanning (nmap, masscan)
- `service_detector.py` - Service identification
- `k8s_detector.py` - Kubernetes cluster detection

**Responsibilities:**
- Network discovery scans
- Service fingerprinting
- K8s cluster auto-detection

---

### 9. User Service (Port 8008)
**Purpose:** Authentication and user management

**Components:**
- `models.py` - User, Team, Role, Permission models
- `schemas.py` - Pydantic request/response schemas
- `app/services/auth_service.py` - JWT, OAuth, MFA
- `app/services/user_service.py` - User CRUD
- `app/services/permission_service.py` - RBAC
- `app/api/v1/auth.py` - Authentication endpoints
- `app/api/v1/users.py` - User management
- `app/api/v1/permissions.py` - Permission endpoints

**Responsibilities:**
- User registration and authentication
- JWT token management
- OAuth2/OIDC integration
- MFA/TOTP support
- Team management
- Cluster access control

---

### 10. Monitoring Service (Port 8009)
**Purpose:** Infrastructure monitoring and alerting

**Components:**
- `health.py` - Health check endpoints
- `metrics.py` - Metrics collection
- `alerts.py` - Alert management
- `services/self_healing.py` - Auto-remediation
- `services/proactive_insights.py` - AI insights

**Responsibilities:**
- Health monitoring
- Metrics collection
- Alert generation
- Self-healing actions
- Proactive insights

---

### 11. Cost Service (Port 8010)
**Purpose:** Cloud cost management and optimization

**Components:**
- `app/services/estimator.py` - Cost estimation
- `app/services/optimizer.py` - Optimization recommendations
- `app/services/anomaly_detector.py` - Cost anomaly detection
- `app/services/collectors/` - Cloud cost collectors

**Responsibilities:**
- AWS/Azure/GCP cost tracking
- Cost estimation for deployments
- Optimization recommendations
- Budget tracking and alerts

---

### 12. Onboarding Service (Port 8011)
**Purpose:** Cluster onboarding and connection management

**Components:**
- `kubeconfig_validator.py` - Kubeconfig validation
- `connection_tester.py` - Cluster connectivity testing
- `vault_integration.py` - Credential storage

**Responsibilities:**
- Kubeconfig validation
- Cluster connection testing
- Secure credential storage

---

### 13. Workflow Service (Port 8012)
**Purpose:** Workflow orchestration and automation

**Components:**
- `models.py` - Workflow definitions
- `tasks.py` - Celery tasks
- `step_handlers.py` - Step execution handlers
- `rollback.py` - Workflow rollback
- `event_publisher.py` - NATS event publishing

**Responsibilities:**
- Workflow execution
- Step orchestration
- Parallel execution
- Rollback support

---

### 14. Notification Service (Port 8013)
**Purpose:** Multi-channel notifications

**Components:**
- `models.py` - Notification models
- `app/services/notification_sender.py` - Channel senders
- `app/api/v1/notifications.py` - Notification API

**Responsibilities:**
- Email notifications
- Slack notifications
- Teams notifications
- PagerDuty integration
- Webhook delivery
- In-app notifications

---

### 15. Frontend (Port 3000)
**Purpose:** User interface

**Components:**
- React 18 application
- TanStack Query for data fetching
- Zustand for state management
- Shadcn UI components
- Socket.io for real-time updates

**Pages:**
- Dashboard (`/`)
- Infrastructure (`/infrastructure`)
- Discovery (`/discovered`)
- Chat (`/chat`)
- Workflows (`/workflows`)
- Monitoring (`/monitoring`)
- Cost (`/cost`)
- Settings (`/settings`)
- Welcome (`/welcome`)

---

## Data Flow Examples

### 1. User Query Flow
```
User → Frontend → API Gateway → AI Router → Agent Service → K8s/AWS/Azure/GCP
                                                                          ↓
User ← Frontend ← API Gateway ← AI Router ← RAG Service ← Qdrant ←───────┘
```

### 2. Action Execution Flow
```
User → Frontend → API Gateway → AI Router → Policy Engine → Action Engine
                                                                          ↓
User ← Frontend ← API Gateway ← AI Router ← Audit Service ←─────────────┘
```

### 3. Cluster Onboarding Flow
```
User → Frontend → API Gateway → Onboarding Service → K8s API (validate)
                                                              ↓
User ← Frontend ← API Gateway ← User Service ← Vault (store creds)
```

### 4. Workflow Execution Flow
```
User → Frontend → API Gateway → Workflow Service → Celery Workers
                                                            ↓
User ← Frontend ← API Gateway ← Agent Service ←────────────┘
```

---

## Database Schema

### PostgreSQL Tables

**users**
- id (UUID, PK)
- email (VARCHAR)
- password_hash (VARCHAR)
- name (VARCHAR)
- role (ENUM)
- team_id (UUID, FK)
- mfa_enabled (BOOLEAN)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

**teams**
- id (UUID, PK)
- name (VARCHAR)
- created_at (TIMESTAMP)

**clusters**
- id (UUID, PK)
- name (VARCHAR)
- kubeconfig (TEXT, encrypted)
- user_id (UUID, FK)
- team_id (UUID, FK)
- status (ENUM)
- created_at (TIMESTAMP)

**discovered_hosts**
- id (UUID, PK)
- ip_address (VARCHAR)
- hostname (VARCHAR)
- ports (JSON)
- services (JSON)
- scan_id (UUID)
- created_at (TIMESTAMP)

**workflows**
- id (UUID, PK)
- name (VARCHAR)
- definition (JSON)
- status (ENUM)
- user_id (UUID, FK)
- created_at (TIMESTAMP)

**audit_logs**
- id (UUID, PK)
- user_id (UUID, FK)
- action (VARCHAR)
- resource_type (VARCHAR)
- resource_id (UUID)
- details (JSON)
- created_at (TIMESTAMP)

---

## Event Flow (NATS)

### Event Subjects

- `discovery.scan.completed` - Discovery scan finished
- `discovery.host.updated` - Host information updated
- `k8s.pod.created` - New pod detected
- `k8s.pod.deleted` - Pod deleted
- `k8s.pod.modified` - Pod updated
- `workflow.execution.started` - Workflow started
- `workflow.execution.completed` - Workflow completed
- `workflow.execution.failed` - Workflow failed
- `alert.created` - New alert generated
- `notification.sent` - Notification delivered

---

## Security

### Authentication
- JWT access tokens (15 min expiry)
- JWT refresh tokens (7 day expiry)
- OAuth2/OIDC (Google, GitHub, Azure AD)
- MFA/TOTP support

### Authorization
- Role-based access control (RBAC)
- Team-based permissions
- Namespace-level cluster access
- Wildcard pattern support (e.g., `*-prod-*`)

### Encryption
- Kubeconfig stored encrypted in database
- Vault integration for secrets
- TLS for all inter-service communication

---

## Deployment

### Docker Compose (Development)
```bash
docker-compose up -d
```

### Kubernetes (Production)
```bash
kubectl apply -k infra/k8s/overlays/production
```

### Helm Chart
```bash
helm install talkai infra/helm/opsai
```

---

## Monitoring

### Metrics
- Prometheus metrics on all services
- Custom Grafana dashboards
- SLA/SLO tracking

### Logging
- Structured JSON logging
- Log aggregation via NATS
- Elasticsearch/Loki integration

### Tracing
- OpenTelemetry integration
- Jaeger for distributed tracing

---

## API Endpoints Summary

| Service | Base URL | Key Endpoints |
|---------|----------|---------------|
| API Gateway | `/api/v1/*` | All routes |
| AI Router | `/ai/v1/*` | `/chat`, `/classify`, `/rag/search` |
| User Service | `/api/v1/auth/*` | `/login`, `/register`, `/refresh` |
| Discovery | `/api/v1/discovery/*` | `/scan`, `/hosts`, `/services` |
| Onboarding | `/api/v1/clusters/*` | `/register`, `/test`, `/connect` |
| Workflow | `/api/v1/workflows/*` | `/execute`, `/status`, `/rollback` |
| Monitoring | `/api/v1/monitoring/*` | `/health`, `/metrics`, `/alerts` |
| Cost | `/api/v1/costs/*` | `/daily`, `/budgets`, `/recommendations` |
| Notification | `/api/v1/notifications/*` | `/send`, `/preferences` |

---

## Technology Stack

### Backend
- **Framework:** FastAPI
- **ORM:** SQLAlchemy (async)
- **Database:** PostgreSQL 16
- **Cache:** Redis 7
- **Message Queue:** Celery + Redis
- **Event Bus:** NATS
- **Vector Store:** Qdrant

### Frontend
- **Framework:** React 18
- **Language:** TypeScript
- **State:** Zustand
- **Data:** TanStack Query
- **UI:** Shadcn UI + Tailwind CSS
- **Real-time:** Socket.io

### Infrastructure Tools
- **Kubernetes:** kubernetes-client (Python)
- **AWS:** boto3
- **Azure:** azure-*
- **GCP:** google-cloud-*

### AI/ML
- **LLM:** OpenAI, Anthropic, Azure OpenAI
- **Embeddings:** OpenAI, HuggingFace
- **Vector DB:** Qdrant

---

*Last Updated: 2026-02-16*
