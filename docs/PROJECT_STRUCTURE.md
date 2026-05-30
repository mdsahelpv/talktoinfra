# TalkToInfra — Project Structure

## Top-Level Layout

```
talktoinfra/
├── docs/                          # Design docs, ADRs, runbooks
├── orchestrator/                  # AI Orchestrator service
├── agent/                         # In-cluster Infra Agent
├── cli/                           # Terminal client
├── web/                           # Web dashboard (React)
├── shared/                        # Shared schemas, types, protos
├── deploy/                        # Deployment configs
├── tests/                         # Integration & e2e tests
├── examples/                      # Example configs, scripts
├── .github/                       # CI/CD workflows
├── .gitignore
├── LICENSE                        # Apache 2.0
├── README.md
├── CONTRIBUTING.md
└── Makefile / Taskfile.yml
```

---

## orchestrator/ — AI Orchestrator

The brain. Runs as a FastAPI service. Routes user queries through LangGraph agents, enforces safety gates, and dispatches to the agent.

```
orchestrator/
├── src/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app entry, lifespan, CORS
│   ├── config.py                      # Pydantic Settings (LLM keys, DB URL, etc.)
│   ├── exceptions.py                  # Custom exception classes
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py                  # Top-level API router
│   │   ├── deps.py                    # Dependency injection (auth, session)
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py                # POST /v1/chat — main conversation endpoint
│   │   │   ├── sessions.py            # CRUD /v1/sessions
│   │   │   ├── tools.py               # GET /v1/tools — list available tools
│   │   │   ├── agents.py              # GET /v1/agents — agent status
│   │   │   ├── audit.py               # GET /v1/audit — action history
│   │   │   └── health.py              # GET /v1/health
│   │   └── ws/
│   │       ├── __init__.py
│   │       └── chat.py                # WebSocket /ws/chat — streaming chat
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent_engine.py            # LangGraph supervisor agent
│   │   ├── agent_registry.py          # Map of sub-agent name → class
│   │   ├── graph.py                   # LangGraph state graph definition
│   │   ├── state.py                   # TypedDict state schema
│   │   ├── router.py                  # Intent classifier → agent router
│   │   └── memory.py                  # Conversation + incident memory
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseAgent abstract class
│   │   ├── supervisor.py              # SupervisorAgent — decomposes tasks
│   │   ├── k8s_agent.py               # Kubernetes agent
│   │   ├── cloud_agent.py             # Cloud (AWS/Azure/GCP) agent
│   │   ├── network_agent.py           # DNS / networking agent
│   │   ├── ad_agent.py                # Active Directory / LDAP agent
│   │   ├── onprem_agent.py            # SSH / systemctl agent
│   │   ├── db_agent.py                # Database agent
│   │   └── monitoring_agent.py        # Prometheus / Grafana agent
│   │
│   ├── safety/
│   │   ├── __init__.py
│   │   ├── gate.py                    # SafetyGate — three-tier permission check
│   │   ├── tiers.py                   # PermissionTier enum (read/mutate/destructive)
│   │   ├── redactor.py                # Secrets / PII redaction before LLM
│   │   └── validator.py               # Tool call arg validation
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py                # LLMProvider abstract interface
│   │   ├── registry.py                # Provider registry (OpenAI, Anthropic, etc.)
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── ollama_provider.py
│   │   ├── azure_provider.py
│   │   ├── bedrock_provider.py
│   │   └── completions.py             # Chat completion helpers
│   │
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── vector_store.py            # Chroma/Qdrant/pgvector wrapper
│   │   ├── embedder.py                # Embedding model interface
│   │   ├── ingester.py                # Runbook / doc ingestion pipeline
│   │   └── retriever.py               # RAG retrieval for agent context
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── chat.py                    # ChatMessage, Conversation, Session
│   │   ├── action.py                  # Action, ActionResult, ActionCatalog
│   │   ├── agent.py                   # AgentConfig, AgentStatus
│   │   ├── audit.py                   # AuditLog entry
│   │   └── user.py                    # User, Role, permissions
│   │
│   └── storage/
│       ├── __init__.py
│       ├── database.py                # SQLAlchemy async engine
│       ├── models.py                  # ORM models (session, audit, incident)
│       ├── repository.py              # CRUD repositories
│       └── migrations/                # Alembic migrations
│
├── tests/
│   ├── conftest.py
│   ├── test_chat.py
│   ├── test_safety_gate.py
│   ├── test_agents/
│   │   ├── test_k8s_agent.py
│   │   ├── test_cloud_agent.py
│   │   └── test_network_agent.py
│   └── test_llm/
│       └── test_providers.py
│
├── Dockerfile
├── pyproject.toml
├── alembic.ini
└── .env.example
```

---

## agent/ — Infra Agent (in-cluster)

The hands. Deployed inside your network/cluster. Connects to actual infrastructure APIs and executes tool calls. Communicates with orchestrator via secure WebSocket or gRPC.

```
agent/
├── src/
│   ├── __init__.py
│   ├── main.py                        # Agent entry point (gRPC or WS client)
│   ├── config.py                      # Agent config (orchestrator URL, creds)
│   │
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseConnector abstract class
│   │   ├── k8s.py                     # Kubernetes connector (official client)
│   │   ├── aws.py                     # AWS connector (boto3)
│   │   ├── azure.py                   # Azure connector (azure-sdk)
│   │   ├── gcp.py                     # GCP connector (google-cloud-sdk)
│   │   ├── ssh.py                     # SSH connector (asyncssh / paramiko)
│   │   ├── ad.py                      # Active Directory connector (ldap3)
│   │   ├── dns.py                     # DNS connector (dnspython)
│   │   ├── ping.py                    # ICMP / ping
│   │   ├── http.py                    # HTTP health check
│   │   ├── db.py                      # Database connector (SQLAlchemy / psycopg)
│   │   ├── prometheus.py              # Prometheus connector
│   │   └── vmware.py                  # vSphere connector (future)
│   │
│   ├── catalog/
│   │   ├── __init__.py
│   │   ├── registry.py                # ActionCatalog — registry of all actions
│   │   ├── base.py                    # BaseAction — typed action definition
│   │   ├── actions/
│   │   │   ├── __init__.py
│   │   │   ├── k8s_get_pods.py
│   │   │   ├── k8s_describe_pod.py
│   │   │   ├── k8s_logs.py
│   │   │   ├── k8s_events.py
│   │   │   ├── k8s_restart_deployment.py
│   │   │   ├── k8s_scale.py
│   │   │   ├── k8s_top.py
│   │   │   ├── cloud_list_instances.py
│   │   │   ├── cloud_start_instance.py
│   │   │   ├── cloud_stop_instance.py
│   │   │   ├── dns_lookup.py
│   │   │   ├── network_ping.py
│   │   │   ├── network_port_check.py
│   │   │   ├── ad_search_user.py
│   │   │   ├── ad_unlock_account.py
│   │   │   ├── ssh_systemctl_status.py
│   │   │   ├── ssh_journalctl.py
│   │   │   ├── ssh_disk_usage.py
│   │   │   ├── prometheus_query.py
│   │   │   └── db_query.py
│   │   └── templates/                 # Action templates / jinja2 for fast creation
│   │
│   ├── executor/
│   │   ├── __init__.py
│   │   ├── executor.py                # Deterministic executor (never shell=True)
│   │   ├── runner.py                  # Runs compiled commands
│   │   ├── timeout.py                 # Per-action timeout enforcement
│   │   └── output.py                  # Output parsing, compaction, truncation
│   │
│   └── client/
│       ├── __init__.py
│       ├── orchestrator_client.py     # gRPC/WS client to orchestrator
│       └── heartbeat.py               # Keepalive / health reporting
│
├── tests/
│   ├── conftest.py
│   ├── connectors/
│   │   ├── test_k8s.py
│   │   ├── test_aws.py
│   │   └── test_dns.py
│   └── catalog/
│       ├── test_registry.py
│       └── actions/
│           ├── test_k8s_get_pods.py
│           └── test_dns_lookup.py
│
├── Dockerfile.agent                   # Minimal agent image
├── pyproject.toml
└── .env.example
```

---

## cli/ — Terminal Client

The primary interface for infra engineers. Beautiful rich terminal with streaming, approval prompts, and feedback.

```
cli/
├── src/
│   ├── __init__.py
│   ├── main.py                        # CLI entry point (click)
│   ├── config.py                      # CLI config (orchestrator URL, API key)
│   │
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── chat.py                    # Interactive chat mode
│   │   ├── ask.py                     # Single question mode
│   │   ├── session.py                 # Session management
│   │   ├── status.py                  # Agent / cluster status
│   │   ├── history.py                 # Past queries & audits
│   │   └── config.py                  # CLI config management
│   │
│   ├── client/
│   │   ├── __init__.py
│   │   ├── api.py                     # REST API client (httpx)
│   │   └── ws.py                      # WebSocket client for streaming
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── chat.py                    # Interactive chat loop
│   │   ├── renderer.py                # Markdown → Rich render
│   │   ├── prompts.py                 # Approval / confirmation prompts
│   │   ├── spinners.py                # Progress indicators
│   │   └── colors.py                  # Theme / ANSI colors
│   │
│   └── utils/
│       ├── __init__.py
│       ├── auth.py                    # API key management
│       ├── output.py                  # Output formatting
│       └── config.py                  # Config file read/write
│
├── tests/
│   ├── test_chat.py
│   └── test_renderer.py
│
├── pyproject.toml
└── .env.example
```

---

## web/ — Web Dashboard

React-based dashboard for team collaboration, visual investigation, approval workflow, and history browsing.

```
web/
├── public/
│   └── favicon.svg
│
├── src/
│   ├── main.tsx                       # App entry
│   ├── App.tsx                        # Router, layout
│   ├── api/
│   │   ├── client.ts                  # API client (fetch/axios)
│   │   ├── chat.ts                    # Chat API + WebSocket hooks
│   │   ├── sessions.ts                # Session API
│   │   └── audit.ts                   # Audit log API
│   │
│   ├── pages/
│   │   ├── Chat.tsx                   # Main chat interface
│   │   ├── Dashboard.tsx              # Cluster / agent overview
│   │   ├── Sessions.tsx               # Session list & history
│   │   ├── Audit.tsx                  # Audit log viewer
│   │   ├── Settings.tsx               # User / LLM / connector settings
│   │   └── Login.tsx                  # Auth page
│   │
│   ├── components/
│   │   ├── chat/
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── InputBar.tsx
│   │   │   ├── ApprovalCard.tsx       # HITL approval widget
│   │   │   └── ToolCallDisplay.tsx    # Show tool calls inline
│   │   ├── dashboard/
│   │   │   ├── StatusCard.tsx
│   │   │   ├── ConnectorList.tsx
│   │   │   └── HealthChart.tsx
│   │   ├── audit/
│   │   │   ├── AuditTable.tsx
│   │   │   └── AuditDetail.tsx
│   │   └── shared/
│   │       ├── Layout.tsx
│   │       ├── Sidebar.tsx
│   │       ├── Loading.tsx
│   │       └── ErrorBoundary.tsx
│   │
│   ├── hooks/
│   │   ├── useChat.ts
│   │   ├── useWebSocket.ts
│   │   └── useSessions.ts
│   │
│   ├── stores/
│   │   └── chatStore.ts               # Zustand / Jotai state
│   │
│   ├── types/
│   │   ├── chat.ts
│   │   ├── action.ts
│   │   └── api.ts
│   │
│   └── styles/
│       └── globals.css
│
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── package.json
└── Dockerfile.web
```

---

## shared/ — Shared Schemas & Protos

```
shared/
├── proto/
│   ├── talktoinfra/
│   │   ├── orchestrator.proto         # gRPC service definitions
│   │   ├── agent.proto                # Agent ↔ Orchestrator messages
│   │   ├── action.proto               # Action catalog definitions
│   │   └── common.proto               # Shared types, enums
│   └── buf.yaml                       # Buf config
│
├── schemas/                           # JSON Schema / Pydantic
│   ├── action.json                    # Action definitions
│   └── tool-call.json                 # Tool call I/O schema
│
└── README.md
```

---

## deploy/ — Deployment & Operations

```
deploy/
├── helm/
│   ├── talktoinfra-orchestrator/      # Helm chart for orchestrator
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── templates/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   ├── ingress.yaml
│   │   │   ├── configmap.yaml
│   │   │   └── _helpers.tpl
│   │   └── README.md
│   │
│   └── talktoinfra-agent/             # Helm chart for in-cluster agent
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── templates/
│       │   ├── deployment.yaml
│       │   ├── serviceaccount.yaml
│       │   ├── rbac.yaml              # Least-privilege RBAC
│       │   ├── configmap.yaml
│       │   └── _helpers.tpl
│       └── README.md
│
├── docker-compose.yml                 # Dev environment (orchestrator + agent + DB)
├── docker-compose.prod.yml            # Production compose
│
├── terraform/                         # (Optional) Deploy infra for orchestrator
│   ├── main.tf
│   └── variables.tf
│
└── scripts/
    ├── setup-dev.sh                   # Dev environment bootstrap
    ├── seed-data.sh                   # Seed sample runbooks / configs
    └── kind-cluster.sh                # Create local Kind cluster for testing
```

---

## tests/ — Integration & E2E

```
tests/
├── conftest.py
├── integration/
│   ├── test_orchestrator_agent.py     # Full orchestrator ↔ agent flow
│   ├── test_chat_to_k8s.py            # "why is pod failing?" → K8s diagnostic
│   ├── test_chat_to_dns.py            # "IP of dns server?" → dig
│   ├── test_chat_to_ad.py             # "where is AD?" → LDAP search
│   ├── test_safety_gate.py            # Read/mutate/destructive enforcement
│   └── test_multiturn.py              # Multi-turn conversation context
│
├── e2e/
│   ├── test_minimal_cluster.py        # Full flow on Kind cluster
│   └── test_mock_infra.py             # Full flow with mocked infra
│
└── fixtures/
    ├── kubeconfig.yaml
    ├── runbook.md
    └── infra_config.json
```

---

## .github/ — CI/CD

```
.github/
├── workflows/
│   ├── ci.yml                         # Lint, type-check, unit tests
│   ├── integration.yml                # Integration tests (Docker Compose)
│   ├── docker-build.yml               # Build & push images
│   └── release.yml                    # Tag + release
│
├── dependabot.yml
└── CODEOWNERS
```

---

## Summary: What We Need to Build

| # | Component | Lang | Lines (est.) | Priority |
|---|-----------|------|-------------|----------|
| 1 | **Shared schemas** (action catalog, protos) | Python + protobuf | ~2,000 | P0 |
| 2 | **Orchestrator core** (FastAPI, LangGraph, safety gate) | Python | ~10,000 | P0 |
| 3 | **Agent connectors** (K8s, DNS, AD, SSH, cloud init) | Python | ~8,000 | P0 |
| 4 | **Action catalog** (30+ typed tools) | Python | ~5,000 | P0 |
| 5 | **CLI client** (rich terminal) | Python | ~4,000 | P0 |
| 6 | **LLM providers** (OpenAI, Anthropic, Ollama) | Python | ~2,000 | P0 |
| 7 | **Knowledge store** (vector DB, RAG, ingestion) | Python | ~2,500 | P1 |
| 8 | **Web dashboard** (React + Tailwind) | TypeScript | ~8,000 | P1 |
| 9 | **Helm charts** (orchestrator + agent) | YAML | ~1,000 | P1 |
| 10 | **Slack bot** | Python | ~2,000 | P2 |
| 11 | **More connectors** (Azure, GCP, VMware, DBs) | Python | ~6,000 | P2 |
| 12 | **Multi-agent routing** (supervisor → sub-agents) | Python | ~3,000 | P2 |
| 13 | **Proactive monitoring** | Python | ~3,000 | P3 |
| 14 | **Enterprise features** (RBAC, SSO, audit) | Python + TS | ~4,000 | P3 |

**Total estimated: ~56,500 lines** for a complete MVP-to-production system.
