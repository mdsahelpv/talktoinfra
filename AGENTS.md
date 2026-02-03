# TalkAI Platform - Agent Guidelines

## Build, Lint & Test Commands

### Python Services (agent-service, api-gateway, ai-router, etc.)

```bash
cd services/<service-name>
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run service with hot reload
uvicorn app.main:app --reload --port <PORT>  # e.g., 8006

# Testing
pytest                                       # Run all tests
pytest tests/test_file.py                   # Run single test file
pytest tests/test_file.py::test_func        # Run single test function
pytest -k "test_name"                       # Run tests matching pattern
pytest --cov=app --cov-report=term-missing  # With coverage

# Linting & Formatting
ruff check .                                # Lint
ruff check . --fix                          # Auto-fix issues
black .                                     # Format code
mypy app/                                   # Type check

# Full quality check
ruff check . && black . --check && mypy app/
```

### Frontend (React/TypeScript)

```bash
cd services/frontend
npm install
npm run dev           # Development server
npm run build         # Production build
npm run lint          # ESLint
npm run preview       # Preview production build
```

### Docker & Local Development

```bash
# Infrastructure only (postgres, redis, qdrant, nats)
docker-compose up -d postgres redis qdrant nats

# Full stack
docker-compose up -d

# Local development helper script
./scripts/local-dev.sh start     # Start all services
./scripts/local-dev.sh stop      # Stop all services
./scripts/local-dev.sh status    # Check service status
./scripts/local-dev.sh logs <service>  # Watch logs
./scripts/health-check.sh        # Check service health
```

## Code Style Guidelines

### Python

#### Imports (3 groups, blank line between)
```python
# 1. Standard library
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

# 2. Third-party packages
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import structlog

# 3. Local application imports
from app.agents.registry import get_agent_registry
from app.config import get_settings
```

#### Type Hints & Naming
- Use `typing` module: `Dict`, `List`, `Optional`, `Any`
- Function signatures must include return types
- `snake_case` for functions, variables, filenames
- `PascalCase` for classes (especially Pydantic models)
- `UPPER_CASE` for constants and enums
- Module-level private vars start with `_`

```python
async def process_task(task_id: str) -> Dict[str, Any]:
    result: Optional[TaskResult] = await fetch_result(task_id)
    return {"status": "completed", "data": result}
```

#### Docstrings (Google-style)
```python
class QueryAgent:
    """Read-only query agent for infrastructure queries.
    
    Safe for auto-execution as all operations are read-only.
    """
    
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

#### Error Handling
```python
try:
    result = await k8s_client.list_pods(namespace)
except ApiException as e:
    logger.error("k8s_api_error", error=str(e), namespace=namespace)
    raise HTTPException(status_code=500, detail=f"Kubernetes API error: {e}")
```

#### Logging (structured with structlog)
```python
logger = structlog.get_logger()
logger.info("task_completed", task_id=task_id, duration_ms=elapsed)
logger.error("operation_failed", error=str(e), operation=operation)
```

#### Configuration
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
// 1. Imports (React, libraries, local)
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';

// 2. Types/Interfaces
interface Props {
  userId: string;
}

// 3. Component
export const UserCard: React.FC<Props> = ({ userId }) => {
  // Implementation
};
```

#### Naming & Path Aliases
- `PascalCase` for components and types
- `camelCase` for functions and variables
- `SCREAMING_SNAKE_CASE` for constants
- Use `@/` alias for src imports: `import { Button } from '@/components/ui/button'`

### General Principles

- **Safety First**: All infrastructure modifications require dry-run + approval
- **Type Safety**: Strict TypeScript and Python type hints required
- **Async Everything**: Prefer async/await over blocking calls
- **Structured Logging**: Always use structured logs with context
- **Error Boundaries**: Handle and log errors at service boundaries
- **Pydantic Validation**: Validate all inputs/outputs with Pydantic
- **Read-Only Auto-Execute**: Query/analysis agents can auto-run; action agents require approval

### Security
- Never commit `.env` files with real secrets
- Use JWT tokens with proper expiration
- Validate all user inputs before processing
- Block dangerous operations at the policy layer

---

## Discovery Service

### Build, Lint & Test Commands

```bash
cd services/discovery-service
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run service with hot reload
uvicorn app.main:app --reload --port 8007

# Testing
pytest                                       # Run all tests
pytest tests/test_file.py                   # Run single test file
pytest tests/test_file.py::test_func        # Run single test function
pytest -k "test_name"                       # Run tests matching pattern
pytest --cov=app --cov-report=term-missing  # With coverage

# Linting & Formatting
ruff check .                                # Lint
ruff check . --fix                          # Auto-fix issues
black .                                     # Format code
mypy app/                                   # Type check

# Full quality check
ruff check . && black . --check && mypy app/
```

### Database Migrations (Alembic)

```bash
cd services/discovery-service

# Create new migration after model changes
alembic revision --autogenerate -m "description"

# Run migrations (upgrade to latest)
alembic upgrade head

# Downgrade one revision
alembic downgrade -1

# View current revision
alembic current

# View migration history
alembic history --verbose
```

### Run Service Locally

```bash
cd services/discovery-service
source venv/bin/activate

# Ensure infrastructure is running
docker-compose up -d postgres redis nats

# Run database migrations
alembic upgrade head

# Start the service
uvicorn app.main:app --reload --port 8007
```

### Run Celery Workers

```bash
cd services/discovery-service
source venv/bin/activate

# Start Celery worker for discovery tasks
celery -A app.celery_app worker --loglevel=info --queues=discovery

# Start Celery beat for scheduled tasks (optional)
celery -A app.celery_app beat --loglevel=info

# Start both worker and beat (development)
celery -A app.celery_app worker --loglevel=info --beat --queues=discovery
```

### Testing Commands

```bash
cd services/discovery-service

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_scanners.py

# Run specific test
pytest tests/test_scanners.py::test_masscan_scan

# Run tests matching pattern
pytest -k "scan"
```

### Key Configuration Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCOVERY_SERVICE_PORT` | Service port | `8007` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/discovery` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `NATS_URL` | NATS connection string | `nats://localhost:4222` |
| `CELERY_BROKER_URL` | Celery broker (Redis) | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://localhost:6379/2` |
| `SCAN_TIMEOUT_SECONDS` | Network scan timeout | `300` |
| `MAX_CONCURRENT_SCANS` | Max parallel scans | `5` |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |

### Scanner Binary Requirements

The Discovery Service requires the following network scanning binaries:

#### masscan
```bash
# Ubuntu/Debian
sudo apt-get install masscan

# macOS
brew install masscan

# Verify installation
masscan --version
```

#### nmap
```bash
# Ubuntu/Debian
sudo apt-get install nmap

# macOS
brew install nmap

# Verify installation
nmap --version
```

**Important:** These binaries must be available in the system PATH. The service runs them as subprocesses for network discovery operations. Ensure proper permissions are set for the user running the service.
