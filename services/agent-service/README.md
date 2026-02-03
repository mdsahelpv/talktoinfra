# Agent Service

Task agents for AI-driven infrastructure operations with production-grade safety.

## Overview

The Agent Service provides specialized agents for infrastructure operations:

- **Query Agent**: Read-only information retrieval (auto-executes)
- **Analysis Agent**: Insights and diagnostics (auto-executes)
- **Planning Agent**: Execution plan generation (auto-executes)
- **Action Agent**: Infrastructure modifications (**requires approval**)

## Safety-First Design

**Core Principle**: ALL infrastructure modifications require human approval.

```
User Request → Agent Planning → Dry-Run Preview → Human Approval → Execute
                                                    ↑
                                              (Mandatory)
```

### Safety Features

- ✅ **Mandatory dry-run** for all actions
- ✅ **Human approval** required for infrastructure changes
- ✅ **Impact analysis** before execution
- ✅ **Rollback capability** on failure
- ✅ **Immutable audit logs** with hash chain
- ✅ **Blocked operations** (delete namespace, etc.)
- ✅ **Risk assessment** based on tool, resource, and environment

## API Endpoints

### Execute Task
```bash
POST /api/v1/agents/execute
Content-Type: application/json

{
  "query": "Show me failing pods in production",
  "environment": "production"
}
```

### Get Task Status
```bash
GET /api/v1/agents/tasks/{task_id}
```

### Approve Action
```bash
POST /api/v1/agents/approvals/{approval_id}/approve
Content-Type: application/json

{
  "decision": "approve",
  "notes": "Approved for deployment window"
}
```

### WebSocket Stream
```bash
ws://localhost:8006/ws?task_id={task_id}
```

## Configuration

Environment variables:

```bash
# Safety
SAFETY_MODE=strict
AUTO_APPROVE_READ_ONLY=true
AUTO_APPROVE_ANALYSIS=true
REQUIRE_APPROVAL_FOR_ACTIONS=all

# Limits
MAX_TASKS_PER_HOUR=50
MAX_PARALLEL_TASKS=5
MAX_TOOL_CALLS_PER_TASK=20

# Timeouts
TASK_TIMEOUT_SECONDS=300
APPROVAL_TIMEOUT_SECONDS=3600
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Agent Service                     │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │  Query   │ │ Analysis │ │  Action  │            │
│  │  Agent   │ │  Agent   │ │  Agent   │            │
│  │  (Auto)  │ │  (Auto)  │ │(Approval)│            │
│  └──────────┘ └──────────┘ └──────────┘            │
│         │            │            │                 │
│         └────────────┼────────────┘                 │
│                      ▼                              │
│  ┌─────────────────────────────────────┐           │
│  │         Safety Engine                │           │
│  │  • Risk Assessment                   │           │
│  │  • Approval Gates                    │           │
│  │  • Blocked Operations                │           │
│  └─────────────────────────────────────┘           │
│                      │                              │
│         ┌────────────┼────────────┐                 │
│         ▼            ▼            ▼                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │   K8s    │ │   AWS    │ │   Audit  │           │
│  │  Tools   │ │  Tools   │ │  Logger  │           │
│  └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────┘
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start service
uvicorn app.main:app --reload --port 8006

# Run tests
pytest tests/
```

## Safety Rules

1. **Read-only operations** can auto-execute
2. **Analysis and planning** can auto-execute
3. **Infrastructure modifications** ALWAYS require approval
4. **Production environment** has additional restrictions
5. **Blocked operations** are never allowed
6. **High-risk resources** require additional scrutiny

## License

MIT
