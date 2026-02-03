# TalkAI Platform - Agent Guidelines

## Build, Lint & Test Commands

### Python Services

All 8 Python services follow the same pattern:

```bash
cd services/<service-name>
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run service
uvicorn app.main:app --reload --port <PORT>

# Testing - single test commands
pytest                                       # Run all tests
pytest tests/test_file.py                   # Run single test file
pytest tests/test_file.py::test_func        # Run single test function
pytest tests/test_file.py::TestClass::test_method
pytest -k "test_pattern"                    # Run tests matching pattern

# Linting & Formatting
ruff check . --fix                          # Lint with auto-fix
black .                                     # Format code
mypy app/                                   # Type check
```

### Discovery Service (Alembic Migrations)

```bash
cd services/discovery-service
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
celery -A app.celery_app worker --loglevel=info --queues=discovery
```

### Frontend (React/TypeScript)

```bash
cd services/frontend
npm install
npm run dev           # Development server
npm run build         # Production build
npm run lint          # ESLint
```

### Docker & Infrastructure

```bash
docker-compose up -d postgres redis qdrant nats  # Infrastructure only
docker-compose up -d                               # Full stack

./scripts/local-dev.sh start     # Start all services
./scripts/local-dev.sh stop      # Stop all services
./scripts/local-dev.sh logs <service>
./scripts/health-check.sh        # Check service health
```

## Code Style Guidelines

### Python

#### Imports (3 groups, blank line between)
```python
# 1. Standard library
import asyncio
from typing import Any, Dict, List, Optional

# 2. Third-party packages
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 3. Local application imports
from app.config import get_settings
```

#### Type Hints & Naming
- Use `typing` module: `Dict`, `List`, `Optional`, `Any`
- Function signatures must include return types
- `snake_case` for functions, variables, filenames
- `PascalCase` for classes (especially Pydantic models)
- `UPPER_CASE` for constants and enums

```python
async def process_task(task_id: str) -> Dict[str, Any]:
    result: Optional[TaskResult] = await fetch_result(task_id)
    return {"status": "completed", "data": result}
```

#### Docstrings (Google-style)
```python
class QueryAgent:
    """Read-only query agent for infrastructure queries."""
    
    async def execute(self, query: str) -> Dict[str, Any]:
        """Execute a read-only query against infrastructure.
        
        Args:
            query: Natural language query string
            
        Returns:
            Dictionary containing query results
            
        Raises:
            HTTPException: If query execution fails
        """
```

#### Error Handling & Logging (structlog)
```python
try:
    result = await k8s_client.list_pods(namespace)
except ApiException as e:
    logger.error("k8s_api_error", error=str(e))
    raise HTTPException(status_code=500, detail=f"Kubernetes API error: {e}")

logger = structlog.get_logger()
logger.info("task_completed", task_id=task_id, duration_ms=elapsed)
```

#### Configuration (Pydantic Settings)
```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    service_port: int = Field(default=8006)
    database_url: str = Field(default="postgresql://...")
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### TypeScript/React

#### File Organization
```typescript
// 1. Imports
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';

// 2. Types
interface Props { userId: string; }

// 3. Component
export const UserCard: React.FC<Props> = ({ userId }) => { };
```

#### Naming & Path Aliases
- `PascalCase` for components and types
- `camelCase` for functions and variables
- `SCREAMING_SNAKE_CASE` for constants
- Use `@/` alias for src imports

## General Principles

- **Safety First**: All infrastructure modifications require dry-run + approval
- **Type Safety**: Strict TypeScript and Python type hints required
- **Async Everything**: Prefer async/await over blocking calls
- **Structured Logging**: Always use structured logs with context
- **Error Boundaries**: Handle and log errors at service boundaries
- **Pydantic Validation**: Validate all inputs/outputs with Pydantic
- **Read-Only Auto-Execute**: Query/analysis agents can auto-run; action agents require approval

## Security

- Never commit `.env` files with real secrets
- Use JWT tokens with proper expiration
- Validate all user inputs before processing
- Block dangerous operations at the policy layer

## Task Execution & Subagent Orchestration

**When implementing tasks from TASKLIST.md, use subagents to parallelize work. This guide prevents overlapping and conflicts.**

### When to Use Subagents vs Direct Execution

**✅ Use Subagents for:**
- Independent tasks across different services (backend + frontend can run in parallel)
- Research/exploration tasks (code analysis, finding patterns)
- Implementation tasks > 30 minutes of focused work
- Testing and validation (can run parallel to development)
- Documentation (can run alongside code changes)

**❌ Do Directly for:**
- Quick fixes < 10 minutes (typos, config tweaks)
- Tasks requiring complex coordination between components
- Final integration and wiring between services
- User communication and clarification questions
- Code review and quality checks

### Parallel vs Sequential Execution

**✅ PARALLEL (Launch simultaneously):**
```
Task A: Create database schema (services/db/)
Task B: Build frontend component (services/frontend/) - NO dependency on schema
Task C: Write API documentation (docs/)
→ All three can run at the same time
```

**❌ SEQUENTIAL (Wait for completion):**
```
Task 1: Create database schema
Task 2: Build API endpoints (NEEDS schema first)
Task 3: Build frontend (NEEDS API first)
→ Must wait for each to finish before starting next
```

**⚠️ DEPENDENT BUT SEPARATE:**
```
Backend: Port 8011 (can build independently)
Frontend: /onboarding page (can build UI, mock API calls)
→ Launch both in parallel, coordinate on API contract
```

### Conflict Prevention Rules

**1. File Ownership (Critical):**
```python
# GOOD - Different files, can run parallel:
Subagent A: services/onboarding-service/app/main.py
Subagent B: services/frontend/src/pages/Onboarding.tsx

# BAD - Same file, WILL CONFLICT:
Subagent A: services/api-gateway/main.py (adding auth)
Subagent B: services/api-gateway/main.py (adding logging)
# → These will overwrite each other's changes!
```

**2. Database Migration Ordering:**
```
Migration 1: 001_initial_schema.py
Migration 2: 002_add_indexes.py  # MUST wait for #1 to be finalized

CORRECT: Create migration 1 → Review → Approve → Create migration 2
```

**3. Shared Dependencies:**
```
❌ DON'T:
Subagent A: Add "requests>=2.28.0" to requirements.txt
Subagent B: Add "requests>=2.25.0" to requirements.txt

✅ DO:
Direct: Update requirements.txt once with all packages
Then launch subagents that use those packages
```

### Launch Strategy by Task Type

**Backend Service Creation (Example: Week 2 - Onboarding Service):**
```
Phase 1 (PARALLEL - 30 min each):
  Subagent 1: "Create service scaffolding (FastAPI, models, config)"
  Subagent 2: "Create database schema and Alembic migrations"

WAIT for both (5 min review)

Phase 2 (PARALLEL - 1 hour each):
  Subagent 3: "Implement API endpoints (POST /register, GET /clusters)"
  Subagent 4: "Write tests for onboarding service (80%+ coverage)"

Direct (30 min):
  - Wire everything together
  - Update docker-compose
  - Test end-to-end
```

**Frontend Feature (Example: Workflow Builder):**
```
Phase 1 (PARALLEL - 1 hour each):
  Subagent 1: "Create React component structure and canvas"
  Subagent 2: "Implement drag-and-drop library integration"
  Subagent 3: "Create API client for workflow data"

WAIT for all

Phase 2 (Direct - 30 min):
  - Integration and state management
  
Phase 3 (PARALLEL):
  Subagent 4: "Write Storybook stories and tests"
```

### How to Launch Subagents

**Command Format:**
```bash
/task "<brief description>" "<detailed instructions>"

Parameters:
- description: 3-5 words max (appears in task list)
- instructions: Full detailed requirements
- subagent_type: explore | general | implement | test
```

**Example Launch:**
```bash
/task "Create onboarding API" "
Implement the onboarding service API in services/onboarding-service/app/api/v1/clusters.py:

REQUIREMENTS:
1. POST /api/v1/clusters/register - Accept kubeconfig JSON
2. POST /api/v1/clusters/{id}/test-connection - Test K8s connectivity
3. GET /api/v1/clusters - List all clusters with pagination
4. DELETE /api/v1/clusters/{id} - Remove cluster

STANDARDS (from AGENTS.md):
- FastAPI with proper type hints
- Pydantic models for request/response validation
- structlog for structured logging
- HTTPException for error handling
- Google-style docstrings
- 80%+ test coverage

DELIVERABLES:
- Complete Python file with all endpoints
- Pydantic models file
- Unit tests file
- Do NOT modify other files
" subagent_type=implement
```

### Quick Reference: TASKLIST.md by Phase

**Phase 0 (Week 1-7) - Subagent Strategy:**

| Week | Task | Subagents | Strategy |
|------|------|-----------|----------|
| 1 | Mock data removal | 1 | Single - focused task |
| 2 | Onboarding Service | 3 | Parallel: backend, frontend, tests |
| 3 | Discovery integration | 2 | Parallel: detection logic, UI |
| 4-5 | Chat workflow | 2 | Parallel: backend API, frontend chat |
| 6 | RAG pipeline | 1 | Single - complex, needs coordination |
| 7 | Monitoring | 2 | Parallel: alerting, dashboard |

**Phase 0 Extension (Week 8-10):**
- Workflow Engine: 4 subagents (service, step types, templates, UI builder)
- AI Engine Settings: 2 subagents (backend config, frontend UI)
- User Experience: 3 subagents (wizard, dashboard, help system)

### Anti-Patterns to Avoid

**❌ DON'T:**
- Launch 20+ subagents at once (resource exhaustion, chaos)
- Have multiple subagents edit the same file
- Skip waiting for dependent tasks
- Use subagents for 5-minute fixes
- Launch subagents that need user input mid-way

**✅ DO:**
- Group independent tasks (3-5 subagents per wave)
- Wait for schema/API contracts before dependent work
- Use direct execution for integration
- Monitor subagent output and retry on failures
- Keep task descriptions under 5 words

### Command Quick Reference

| Task Type | Subagent? | Duration | Parallel? |
|-----------|-----------|----------|-----------|
| Research/Exploration | Yes | 10-30 min | Yes |
| Service scaffolding | Yes | 30-60 min | Yes |
| API implementation | Yes | 1-2 hours | Yes |
| Frontend component | Yes | 1-3 hours | Yes |
| Database migration | No | 15 min | No |
| Integration/wiring | No | 30 min | No |
| Tests | Yes | 1-2 hours | Yes |
| Documentation | Yes | 30 min | Yes |
| Bug fix (< 10 min) | No | 5-10 min | No |
| Code review | No | 15 min | No |
| Final validation | Yes | 30 min | No |

### Example: "Implement Week 2 - Onboarding Service"

```
User: "Implement Phase 0 Week 2 - Onboarding Service"

EXECUTION PLAN:

1. Direct: Read TASKLIST.md section 0.2 (5 min)
   - Understand all requirements

2. Phase 1 - Launch PARALLEL (immediately):
   
   Subagent 1: "Create onboarding backend scaffolding"
   - FastAPI app factory
   - Pydantic settings (Port 8011)
   - SQLAlchemy models (clusters table)
   - requirements.txt, Dockerfile
   
   Subagent 2: "Build onboarding frontend wizard"
   - 5-step ConnectWizard component
   - ConnectionDashboard component
   - API client (onboarding.ts)
   - TypeScript types

3. WAIT for Phase 1 completion (10 min)
   - Review both outputs
   - Verify no conflicts

4. Phase 2 - Launch PARALLEL:
   
   Subagent 3: "Implement K8s cluster onboarding API"
   - POST /register endpoint
   - Kubeconfig validation
   - Vault credential storage
   - Connection testing logic
   
   Subagent 4: "Write onboarding service tests"
   - Unit tests for registration
   - Integration tests
   - Mock Vault for testing
   - 80%+ coverage

5. Direct: Integration (30 min)
   - Wire frontend to backend
   - Test end-to-end flow
   - Update docker-compose.yml
   - Run health checks

6. Phase 3 - Validation:
   
   Subagent 5: "Validate onboarding service"
   - Test with docker-compose
   - Real kubeconfig registration
   - Verify Vault storage
   - Frontend wizard E2E test

7. Direct: Final review and completion
```
