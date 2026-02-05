# TalkAI RAG Service

Retrieval-Augmented Generation Service for Infrastructure Data - Port 8012

## Overview

The RAG Service provides semantic search and retrieval capabilities for infrastructure data using vector embeddings. This service is critical for preventing AI hallucinations by providing grounded context for AI queries.

## Architecture

### 3-Layer Storage Architecture

1. **Layer 1: Structured Storage (PostgreSQL)**
   - Enhanced discovery tables with RAG metadata
   - K8s resource tables (pods, deployments, services, nodes)
   - Index tracking and citation storage

2. **Layer 2: Elasticsearch/OpenSearch**
   - `infrastructure-logs` - Pod logs, system logs
   - `infrastructure-events` - K8s events, scan events
   - `infrastructure-configs` - ConfigMaps, Secrets (redacted)

3. **Layer 3: Vector Embeddings (Qdrant)**
   - `infrastructure-resources` - Embeddings of all infrastructure
   - `infrastructure-logs` - Embeddings of log patterns
   - `infrastructure-docs` - Documentation embeddings
   - `k8s-resources` - K8s resource embeddings

## Features

- **Semantic Search**: Natural language queries against infrastructure data
- **Source Citations**: Full traceability of information sources
- **Incremental Indexing**: Track indexed documents for efficient updates
- **Event-Driven Pipeline**: NATS-based indexing triggers
- **Multi-Collection Support**: Separate collections for different data types

## API Endpoints

### Search API (`/api/v1/rag/search`)
- `POST /` - Perform RAG search
- `GET /` - Simple GET search
- `POST /context` - Get context with citations
- `POST /batch` - Batch search

### Index API (`/api/v1/rag/index`)
- `GET /health` - Health check
- `GET /collections` - List collections
- `POST /collections/{name}` - Create collection
- `DELETE /collections/{name}` - Delete collection
- `POST /index` - Trigger indexing job
- `GET /jobs/{id}` - Get job status

### Sources API (`/api/v1/rag/sources`)
- `POST /cite` - Create citation
- `GET /cite/{key}` - Get citation
- `GET /query/{hash}` - Get citations by query
- `GET /source/{type}/{id}` - Get citations by source

## Configuration

### Environment Variables

```bash
# Service
RAG_SERVICE_PORT=8012
RAG_DEBUG=false

# Database
RAG_DATABASE_URL=postgresql://opsai:changeme@postgres:5432/opsai
RAG_DATABASE_URL_ASYNC=postgresql+asyncpg://opsai:changeme@postgres:5432/opsai

# Redis
RAG_REDIS_URL=redis://redis:6379/5

# Qdrant
RAG_QDRANT_URL=http://qdrant:6333
RAG_QDRANT_API_KEY=

# Embedding Model
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_EMBEDDING_BATCH_SIZE=32
RAG_EMBEDDING_DEVICE=cpu

# RAG Settings
RAG_SIMILARITY_THRESHOLD=0.7
RAG_TOP_K=10
RAG_MAX_CONTEXT_LENGTH=4000

# Collections
RAG_COLLECTION_INFRASTRUCTURE=infrastructure-resources
RAG_COLLECTION_LOGS=infrastructure-logs
RAG_COLLECTION_DOCS=infrastructure-docs
RAG_COLLECTION_K8S_RESOURCES=k8s-resources

# NATS
RAG_NATS_URL=nats://nats:4222
RAG_NATS_RAG_CHANNEL=rag.index

# CORS
RAG_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

## Running Locally

```bash
cd services/rag-service

# Create virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run service
uvicorn main:app --reload --port 8012
```

## Running with Docker

```bash
docker-compose up -d rag-service
```

## Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov-report=html

# Run specific test
pytest tests/test_search.py
```

## Linting

```bash
# Check code style
ruff check .

# Auto-fix
ruff check . --fix

# Format code
black .

# Type checking
mypy services/
```

## Project Structure

```
services/rag-service/
├── config.py              # Configuration settings
├── main.py               # FastAPI application
├── database.py           # Database connection
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── api/
│   └── v1/
│       ├── index.py     # Index management endpoints
│       ├── search.py    # Search endpoints
│       └── sources.py   # Citation endpoints
├── services/
│   ├── embedder.py      # Embedding generation
│   ├── indexer.py       # Qdrant management
│   └── pipeline.py      # Data transformation
├── Dockerfile
├── requirements.txt
└── README.md
```

## RAG Query Flow

```
User Query → Embed Query → Semantic Search in Qdrant
                              ↓
                        Retrieve top-K results
                              ↓
                        Extract source citations
                              ↓
                        Build prompt with context + citations
                              ↓
                        Return answer with sources
```

## Integration

### From Discovery Service
When new hosts/ports are discovered, publish events to NATS for automatic indexing.

### From AI Router
Call RAG search to retrieve context before generating responses.

### From Frontend
Use the search API to provide semantic search functionality.

## License

MIT
