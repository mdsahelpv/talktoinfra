# AI-Driven Infrastructure Operations Platform

A production-ready, on-premise AI platform for infrastructure operations with semantic search, natural language queries, and controlled action execution.

**Status**: MVP Phase 1 Complete  
**Version**: 1.0.0  
**License**: MIT

---

## 🎯 Overview

This platform enables DevOps and SRE teams to manage infrastructure through natural language conversations with enterprise-grade safety controls.

### Key Features

- **🔍 Semantic Search**: Vector-based infrastructure search using Qdrant
- **💬 Natural Language**: Query infrastructure in plain English via Ollama LLMs
- **🛡️ Dry-Run Safety**: All actions validated before execution
- **📋 RBAC**: Role-based access control with approval workflows
- **📊 Audit Logging**: Complete action trail for compliance
- **🔄 Real-time**: WebSocket support for live updates
- **🏢 Enterprise-Ready**: On-premise deployment, SOC 2 aligned

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TalkAI Platform                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────────┐    │
│  │   Web UI     │     │   API GW     │     │      AI Core             │    │
│  │  (Next.js)   │◄───►│   (Nginx)    │◄───►│    (FastAPI)             │    │
│  │   :3000      │     │    :80       │     │     :8000                │    │
│  └──────────────┘     └──────────────┘     └──────────┬─────────────────┘    │
│                                                       │                      │
│                                ┌──────────────────────┼──────────────┐      │
│                                │                      │              │      │
│                       ┌────────▼─────────┐  ┌─────────▼────────┐    │      │
│                       │  LLM Manager     │  │   Chat Engine    │    │      │
│                       │  (Ollama SDK)    │  │  (Streaming WS)  │    │      │
│                       └────────┬─────────┘  └──────────────────┘    │      │
│                                │                                    │      │
│                       ┌────────▼─────────┐  ┌──────────────────┐   │      │
│                       │  Model Router    │  │  Template Engine │   │      │
│                       │ (Fallback Logic) │  │  (System Prompts)│   │      │
│                       └────────┬─────────┘  └──────────────────┘   │      │
│                                │                                    │      │
│  ┌─────────────────────────────┼────────────────────────────────────┘      │
│  │         Data Layer          │                                           │
│  ├─────────────────────────────┤                                           │
│  │  PostgreSQL │ Redis │ MinIO │                                           │
│  │   (Auth)    │(Cache)│(Files)│                                           │
│  └─────────────────────────────┘                                           │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                         AI Services (Ollama)                          │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │ │
│  │  │  LLaMA 2   │  │  Mistral   │  │  Codellama │  │  Custom Models │  │ │
│  │  │  :11434    │  │  :11434    │  │  :11434    │  │    :11434      │  │ │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Microservices (7 Services)

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (Port 8000)                   │
│              Auth • Rate Limiting • Routing                  │
└─────────────────────────────────────────────────────────────┘
                               │
     ┌───────────┬───────────┬───────────┬───────────┐
     ▼           ▼           ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│AI Router│ │ Action  │ │ Policy  │ │Ingestion│ │  Audit  │
│  8001   │ │ Engine  │ │ Engine  │ │ Service │ │ Service │
│         │ │  8002   │ │  8003   │ │  8004   │ │  8005   │
│- Intent │ │- Dry-   │ │- RBAC   │ │- K8s    │ │- Logs   │
│- RAG    │ │  Run    │ │- Appro- │ │- Embed  │ │- Comp-  │
│- LLM    │ │- Sandbox│ │  vals   │ │- Search │ │  liance │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
     │           │           │           │           │
     └───────────┴───────────┴───────────┴───────────┘
                               │
     ┌───────────────────────┬───────────┬───────────┐
     ▼                       ▼           ▼           ▼
┌─────────┐            ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Ollama  │            │  K8s    │ │PostgreSQL││  Redis  │
│ (LLM)   │            │  API    │ │ (Data)  │ │ (Cache) │
└─────────┘            └─────────┘ └─────────┘ └─────────┘
     │                       │
     ▼                       ▼
┌─────────┐            ┌─────────┐
│ Qdrant  │            │  NATS   │
│(Vectors)│            │ (Queue) │
└─────────┘            └─────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Tailwind CSS, shadcn/ui |
| **API Gateway** | FastAPI, Kong (future) |
| **AI Services** | Python 3.11, FastAPI, Ollama |
| **Vector DB** | Qdrant |
| **Cache** | Redis 7 |
| **Database** | PostgreSQL 16 |
| **Queue** | NATS |
| **LLM** | Ollama (LLaMA 3.3 70B, CodeLlama 34B) |
| **Monitoring** | Prometheus, Grafana |
| **Security** | JWT, RBAC, mTLS |

---

## 🚀 Quick Start

### Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.20+
- Ollama (local or remote)
- 8GB+ RAM recommended

### Option 1: Docker Compose (Recommended for Development)

```bash
# Clone repository
cd /home/ubuntu/talkai

# Quick setup with automated script
./scripts/quickstart.sh

# Or manual setup:
# Copy environment configuration
cp .env.example .env

# Edit .env with your settings
# - Set OLLAMA_HOST to your Ollama server
# - Change default passwords

# Start all services
docker-compose -f infra/docker/docker-compose.yml up -d

# Check service health
./scripts/health-check.sh

# Access platform
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Kubernetes + Helm (Production)

```bash
# Install using Helm
helm repo add talkai https://charts.talkai.io
helm repo update

# Development
kubectl apply -k infra/k8s/overlays/development/

# Production with Helm
helm install talkai ./infra/helm/opsai \
  --namespace talkai \
  --create-namespace \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=talkai.yourdomain.com \
  --set secrets.admin.password=your-secure-password

# Check status
kubectl get pods -n talkai
kubectl get svc -n talkai
kubectl get ingress -n talkai
```

---

## 📁 Project Structure

```
talkai/
├── services/                    # Microservices
│   ├── api-gateway/            # Port 8000 - Entry point
│   ├── ai-router/              # Port 8001 - Intent & LLM
│   ├── action-engine/          # Port 8002 - Action execution
│   ├── policy-engine/          # Port 8003 - RBAC & approvals
│   ├── ingestion-service/      # Port 8004 - Data ingestion
│   ├── audit-service/          # Port 8005 - Audit logging
│   └── frontend/               # Port 3000 - React UI
├── infra/                       # Infrastructure
│   ├── docker/                 # Docker Compose
│   ├── helm/                   # Helm charts
│   │   └── opsai/             # Main Helm chart
│   │       ├── templates/     # K8s templates
│   │       │   ├── _helpers.tpl
│   │       │   ├── secrets.yaml
│   │       │   ├── configmap.yaml
│   │       │   ├── deployment.yaml
│   │       │   ├── service.yaml
│   │       │   ├── ingress.yaml
│   │       │   ├── hpa.yaml
│   │       │   └── NOTES.txt
│   │       └── values.yaml
│   └── k8s/                    # Kubernetes manifests
├── docs/                        # Documentation
│   ├── PRD.md                  # Product Requirements
│   ├── DEPLOYMENT.md           # Deployment Guide
│   └── ARCHITECTURE.md         # Architecture Details
├── shared/                      # Shared code
│   ├── schemas/                # JSON schemas
│   └── clients/                # Service clients
└── scripts/                     # Helper scripts
    ├── quickstart.sh           # Quick start script
    ├── health-check.sh         # Health check script
    └── test.sh                 # Test runner
```

---

## 🔧 Environment Setup

### Required Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `DATABASE_URL` | `postgresql://user:pass@postgres:5432/talkai` | Database connection |
| `REDIS_URL` | `redis://redis:6379` | Redis connection |
| `JWT_SECRET` | `your-secret-key` | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRATION_MINUTES` | `60` | Token expiration |
| `API_GATEWAY_PORT` | `8000` | API Gateway port |
| `ENVIRONMENT` | `development` | Environment name |
| `ENABLE_MOCK_RESPONSES` | `false` | Enable mock LLM responses |
| `ENABLE_RATE_LIMITING` | `true` | Enable API rate limiting |
| `ENABLE_AUDIT_LOG` | `true` | Enable audit logging |

See `.env.example` for full configuration options.

---

## 🚫 No Mock Data Policy

**Critical**: This codebase strictly prohibits mock data in production code.

### Policy

Mock data, mock functions, and testing utilities **must not** exist in production code. They are allowed **only** in:
- Test files (`test_*.py`, `*_test.py`)
- Test directories (`tests/`, `test/`)
- Test fixtures and configuration

### What's Prohibited

Production code must not contain:
- Mock functions (`_get_mock_resources`, `get_mock_namespaces`, etc.)
- Mock variables (`mock_data`, `MOCK_DATA`, `fake_data`, etc.)
- Testing utilities (`MagicMock`, `Mock`, `@patch` decorators)
- Hardcoded "test-" prefixes in resource identifiers
- JSON/YAML mock data files outside of test directories

### Enforcement

We enforce this policy through multiple safeguards:

1. **Pre-Commit Hooks**: Automatically blocks commits with mock data in production files
2. **CI/CD Pipeline**: First job in CI runs mock detection and fails the build if found
3. **Detection Script**: `scripts/check-no-mock.py` scans for mock patterns

### Example Violations

```python
# ❌ WRONG - Mock data in production code
async def _get_mock_resources():
    return [{"name": "mock-pod", "status": "running"}]

mock_data = {
    "namespaces": ["test-ns-1", "test-ns-2"]
}

from unittest.mock import MagicMock
mock_client = MagicMock()
```

```python
# ✅ CORRECT - Production code uses real data
async def get_resources_from_cluster(cluster_id: str):
    client = kubernetes_client.get_client(cluster_id)
    return await client.list_pods()
```

```python
# ✅ CORRECT - Mock data only in tests
def test_resource_service():
    mock_data = [{"name": "test-pod", "status": "running"}]
    with patch("app.services.get_resources") as mock:
        mock.return_value = mock_data
        result = service.get_resources()
        assert result == mock_data
```

### Bypassing (Not Recommended)

To bypass pre-commit hooks temporarily:
```bash
git commit --no-verify
```

### Why This Matters

- **Safety**: Prevents accidental deployment of mock data to production
- **Clarity**: Clear separation between production and test code
- **Quality**: Production code is clean, professional, and focused
- **Trust**: Developers can trust that production code contains only real logic

See [docs/ADR/ADR-001-no-mock-data.md](docs/ADR/ADR-001-no-mock-data.md) for full Architecture Decision Record.

---

## 🔐 Security Considerations

### Authentication
- JWT-based authentication
- Corporate SSO ready (SAML/OIDC)
- Token refresh mechanism
- Session management

### Authorization
- Role-Based Access Control (RBAC)
  - Super Admin, Admin, Senior Engineer, Engineer, Read-Only, Auditor
- Resource-level permissions
- Time-based access restrictions

### Action Safety
- **Dry-Run Default**: All actions simulate first
- **Multi-Level Approvals**: Up to 3 approval levels
- **Impact Analysis**: Detect cascade effects
- **Rollback Plans**: Automatic rollback capability

### Secrets Management
- **JWT Tokens**: Use strong secrets (32+ chars), rotate regularly
- **Database**: Enable SSL, use connection pooling, limit privileges
- **API**: Rate limiting enabled by default (10 req/s per IP)
- **CORS**: Configure allowed origins in production
- **Secrets**: Never commit `.env` files, use Kubernetes secrets
- **Models**: Audit downloaded models, validate checksums
- **Network**: Use internal networks between services
- **Monitoring**: Enable audit logging for all API calls

### Production Checklist

- [ ] Change default admin password
- [ ] Use strong JWT secret (32+ characters)
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS origins (not `*`)
- [ ] Set up log aggregation
- [ ] Enable monitoring (Prometheus/Grafana)
- [ ] Configure backup for PostgreSQL
- [ ] Set resource limits for pods
- [ ] Enable HPA for auto-scaling
- [ ] Review RBAC policies
- [ ] Enable mTLS between services
- [ ] Configure secrets management (Vault)
- [ ] Complete security audit
- [ ] Performance testing

### Audit & Compliance
- **Immutable Logs**: SHA-256 hashed audit trail
- **Complete Visibility**: Every query and action logged
- **Export Formats**: JSON, CSV, PDF
- **Retention**: 7 years for compliance

---

## 🛠️ Development Guide

### Local Development Setup

```bash
# Backend
cd services/api-gateway
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd services/frontend
npm install
npm run dev

# AI Router Service
cd services/ai-router
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### API Documentation

Once running, API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Running Tests

```bash
# Backend tests
cd services/api-gateway
pytest

# Frontend tests
cd services/frontend
npm test

# Integration tests
./scripts/test.sh

# Health check
./scripts/health-check.sh
```

### Health Checks

```bash
# Check all services
./scripts/health-check.sh

# Or manually
curl http://localhost:8000/health
curl http://localhost:3000/api/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

---

## 📊 API Reference

### Authentication
```bash
# Login
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin"
}
```

### Query
```bash
# Submit natural language query
POST /api/v1/query
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "Show me failing pods in production",
  "conversation_id": "conv-123"
}
```

### Actions
```bash
# Dry-run action
POST /api/v1/actions/dry-run
Authorization: Bearer <token>

{
  "action": "restart deployment auth-service",
  "target": "auth-service",
  "dry_run": true
}

# Execute approved action
POST /api/v1/actions/execute
Authorization: Bearer <token>

{
  "action_id": "action-456"
}
```

### Approvals
```bash
# List pending approvals
GET /api/v1/approvals/pending
Authorization: Bearer <token>

# Approve action
POST /api/v1/approvals/{id}/approve
Authorization: Bearer <token>
```

---

## 📈 Monitoring

### Metrics Endpoints
- API Gateway: `http://localhost:8000/metrics`
- Prometheus scraping configured

### Health Checks
```bash
# All services
./scripts/health-check.sh
```

### Logging
- Structured JSON logging with structlog
- Correlation IDs across services
- Centralized log aggregation ready

---

## 🗺️ Roadmap

### Phase 1: MVP (Complete) ✅
- Core chat interface
- Basic K8s queries
- Intent classification
- Vector search
- Docker Compose deployment

### Phase 2: Production (Months 4-5) 🚧
- Action execution with dry-run
- Approval workflows
- Enhanced RBAC
- SSO integration
- K8s deployment
- SOC 2 readiness

### Phase 3: Scale (Months 6-8)
- Multi-cluster support
- Cloud providers (AWS, Azure, GCP)
- AI-powered anomaly detection
- Advanced analytics

### Phase 4: Enterprise (Months 9-12)
- Custom integrations
- Workflow automation
- Mobile app
- Advanced compliance

---

## 📚 Documentation

- [Product Requirements (PRD)](docs/PRD.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [API Reference](docs/API.md)
- [Security Guide](docs/SECURITY.md)
- [Service READMEs](services/*/README.md)

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Submit Pull Request

See `CONTRIBUTING.md` for details.

---

## ⚠️ Important Notes

### Ollama Server
The platform requires an Ollama server running separately:
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull required models
ollama pull llama3.3:70b
ollama pull codellama:34b
ollama pull nomic-embed-text

# Start server
ollama serve
```

### Security Warning
**This is an MVP progressing toward production.** Before production use:
- Change all default passwords
- Enable mTLS between services
- Configure proper secrets management (Vault)
- Enable audit logging
- Complete security audit
- Performance testing

---

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/yourorg/talkai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourorg/talkai/discussions)
- **Email**: support@talkai.io

---

**Built with ❤️ for infrastructure teams**
