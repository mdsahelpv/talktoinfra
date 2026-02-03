"""
Ingestion Service

Ingests infrastructure data from various sources and generates vector embeddings.
Provides semantic search capabilities and background workers for continuous ingestion.
Integrates with Qdrant for vector storage.
"""

import asyncio
import hashlib
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware

from config import Settings, get_settings
from models import (
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    ResourceDocument,
    IngestionJob,
    IngestionJobStatus,
)
from embedding import EmbeddingGenerator
from k8s_client import KubernetesClient
from worker import BackgroundWorker

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# In-memory job store (replace with database in production)
job_store: Dict[str, IngestionJob] = {}

# Service components
embedding_generator: Optional[EmbeddingGenerator] = None
k8s_client: Optional[KubernetesClient] = None
worker: Optional[BackgroundWorker] = None
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global embedding_generator, k8s_client, worker, http_client

    settings = get_settings()

    logger.info("ingestion_service_initializing", port=settings.service_port)

    # Initialize components
    embedding_generator = EmbeddingGenerator(
        ollama_host=settings.ollama_host,
        model=settings.embedding_model,
    )
    k8s_client = KubernetesClient()
    worker = BackgroundWorker(
        qdrant_url=settings.qdrant_url,
        collection=settings.qdrant_collection,
    )
    http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    )

    # Start background worker
    await worker.start()

    logger.info("ingestion_service_ready")

    yield

    # Cleanup
    if worker:
        await worker.stop()
    if http_client:
        await http_client.aclose()
    logger.info("ingestion_service_shutting_down")


app = FastAPI(
    title="AI Infrastructure Operations - Ingestion Service",
    description="Ingest infrastructure data and generate embeddings for semantic search",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests with context."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    with structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    ):
        logger.info("request_started")
        response = await call_next(request)
        logger.info("request_completed", status_code=response.status_code)
        return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health = {
        "status": "healthy",
        "service": "ingestion-service",
        "timestamp": time.time(),
        "components": {},
    }

    # Check embedding generator
    try:
        await embedding_generator.health_check()
        health["components"]["embedding_generator"] = "healthy"
    except Exception as e:
        health["components"]["embedding_generator"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"

    # Check Qdrant connection via worker
    try:
        await worker.health_check()
        health["components"]["vector_store"] = "healthy"
    except Exception as e:
        health["components"]["vector_store"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"

    return health


@app.post("/ingest/kubernetes", response_model=IngestResponse)
async def ingest_kubernetes(
    request: Request,
    ingest_req: IngestRequest,
    background_tasks: BackgroundTasks,
):
    """Ingest Kubernetes resources."""
    try:
        job_id = str(uuid.uuid4())
        logger.info(
            "k8s_ingestion_started",
            job_id=job_id,
            namespaces=ingest_req.namespaces,
            resource_types=ingest_req.resource_types,
        )

        # Create job record
        job = IngestionJob(
            job_id=job_id,
            source_type="kubernetes",
            status=IngestionJobStatus.PENDING,
            namespaces=ingest_req.namespaces,
            resource_types=ingest_req.resource_types,
            created_at=datetime.utcnow(),
        )
        job_store[job_id] = job

        # Start background processing
        background_tasks.add_task(
            process_k8s_ingestion,
            job_id,
            ingest_req,
        )

        # Update status
        job.status = IngestionJobStatus.RUNNING
        job.started_at = datetime.utcnow()

        logger.info("k8s_ingestion_job_created", job_id=job_id)

        return IngestResponse(
            job_id=job_id,
            status=job.status,
            message="Kubernetes ingestion job started",
            estimated_completion="2-5 minutes",
        )

    except Exception as e:
        logger.error("k8s_ingestion_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )


@app.post("/ingest/generic", response_model=IngestResponse)
async def ingest_generic(
    request: Request,
    documents: List[ResourceDocument],
    source_type: str,
):
    """Ingest generic resource documents."""
    try:
        job_id = str(uuid.uuid4())
        logger.info(
            "generic_ingestion_started",
            job_id=job_id,
            doc_count=len(documents),
            source_type=source_type,
        )

        # Process documents
        processed = await process_documents(documents, source_type)

        logger.info(
            "generic_ingestion_completed",
            job_id=job_id,
            processed_count=len(processed),
        )

        return IngestResponse(
            job_id=job_id,
            status=IngestionJobStatus.COMPLETED,
            message=f"Successfully ingested {len(processed)} documents",
            documents_processed=len(processed),
        )

    except Exception as e:
        logger.error("generic_ingestion_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )


@app.get("/search", response_model=SearchResponse)
async def semantic_search(
    query: str,
    top_k: int = 5,
    namespace: Optional[str] = None,
    resource_type: Optional[str] = None,
):
    """Perform semantic search over ingested resources."""
    try:
        logger.info(
            "semantic_search",
            query=query[:50],
            top_k=top_k,
        )

        # Generate query embedding
        query_embedding = await embedding_generator.generate(query)

        # Search in vector store
        results = await worker.search(
            embedding=query_embedding,
            top_k=top_k,
            filters={
                "namespace": namespace,
                "resource_type": resource_type,
            },
        )

        # Convert to response model
        search_results = [
            SearchResult(
                id=result["id"],
                score=result["score"],
                resource_type=result["payload"].get("resource_type", "unknown"),
                name=result["payload"].get("name", "unknown"),
                namespace=result["payload"].get("namespace"),
                description=result["payload"].get("description", ""),
                metadata=result["payload"].get("metadata", {}),
            )
            for result in results
        ]

        logger.info(
            "search_completed",
            query=query[:50],
            results_count=len(search_results),
        )

        return SearchResponse(
            query=query,
            results=search_results,
            total_results=len(search_results),
        )

    except Exception as e:
        logger.error("search_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@app.get("/jobs/{job_id}", response_model=IngestionJob)
async def get_job(job_id: str):
    """Get ingestion job status."""
    if job_id not in job_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job_store[job_id]


@app.get("/jobs", response_model=List[IngestionJob])
async def list_jobs(
    status: Optional[IngestionJobStatus] = None,
    limit: int = 50,
):
    """List ingestion jobs."""
    jobs = list(job_store.values())

    if status:
        jobs = [j for j in jobs if j.status == status]

    # Sort by created_at descending
    jobs.sort(key=lambda x: x.created_at, reverse=True)

    return jobs[:limit]


async def process_k8s_ingestion(job_id: str, ingest_req: IngestRequest):
    """Background task to process Kubernetes ingestion."""
    job = job_store[job_id]
    documents: List[ResourceDocument] = []

    try:
        # Fetch resources from Kubernetes
        for namespace in ingest_req.namespaces:
            for resource_type in ingest_req.resource_types:
                try:
                    resources = await k8s_client.get_resources(
                        namespace=namespace,
                        resource_type=resource_type,
                    )

                    for resource in resources:
                        doc = ResourceDocument(
                            id=f"{namespace}/{resource_type}/{resource['name']}",
                            resource_type=resource_type,
                            name=resource["name"],
                            namespace=namespace,
                            description=generate_description(resource_type, resource),
                            content=json.dumps(resource),
                            metadata={
                                "labels": resource.get("labels", {}),
                                "annotations": resource.get("annotations", {}),
                                "created_at": resource.get("created_at"),
                                "status": resource.get("status", {}),
                            },
                        )
                        documents.append(doc)

                except Exception as e:
                    logger.error(
                        "resource_fetch_failed",
                        namespace=namespace,
                        resource_type=resource_type,
                        error=str(e),
                    )

        # Generate embeddings and store
        await process_documents(documents, "kubernetes")

        # Update job status
        job.status = IngestionJobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.documents_processed = len(documents)

        logger.info(
            "k8s_ingestion_completed",
            job_id=job_id,
            documents_processed=len(documents),
        )

    except Exception as e:
        job.status = IngestionJobStatus.FAILED
        job.error_message = str(e)
        logger.error("k8s_ingestion_job_failed", job_id=job_id, error=str(e))


async def process_documents(
    documents: List[ResourceDocument],
    source_type: str,
) -> List[ResourceDocument]:
    """Process documents by generating embeddings and storing them."""
    processed = []

    for doc in documents:
        try:
            # Generate embedding
            text_to_embed = f"{doc.name} {doc.description} {doc.content}"
            embedding = await embedding_generator.generate(text_to_embed)

            # Store in vector database
            await worker.store_document(
                document_id=doc.id,
                embedding=embedding,
                payload={
                    "resource_type": doc.resource_type,
                    "name": doc.name,
                    "namespace": doc.namespace,
                    "description": doc.description,
                    "metadata": doc.metadata,
                    "source_type": source_type,
                    "ingested_at": datetime.utcnow().isoformat(),
                },
            )

            processed.append(doc)

        except Exception as e:
            logger.error(
                "document_processing_failed",
                doc_id=doc.id,
                error=str(e),
            )

    return processed


def generate_description(resource_type: str, resource: Dict[str, Any]) -> str:
    """Generate a human-readable description of a resource."""
    descriptions = {
        "pod": lambda r: f"Pod {r.get('name')} in namespace {r.get('namespace', 'default')} "
        f"with status {r.get('status', {}).get('phase', 'unknown')} "
        f"and {len(r.get('spec', {}).get('containers', []))} containers",
        "deployment": lambda r: f"Deployment {r.get('name')} with "
        f"{r.get('spec', {}).get('replicas', 0)} replicas "
        f"using image {get_deployment_image(r)}",
        "service": lambda r: f"Service {r.get('name')} of type "
        f"{r.get('spec', {}).get('type', 'ClusterIP')} "
        f"exposing ports {get_service_ports(r)}",
        "configmap": lambda r: f"ConfigMap {r.get('name')} with "
        f"{len(r.get('data', {}))} data entries",
        "secret": lambda r: f"Secret {r.get('name')} of type {r.get('type', 'Opaque')}",
    }

    generator = descriptions.get(resource_type.lower())
    if generator:
        return generator(resource)

    return f"{resource_type.capitalize()} {resource.get('name')}"


def get_deployment_image(resource: Dict[str, Any]) -> str:
    """Extract image from deployment spec."""
    containers = (
        resource.get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("containers", [])
    )
    if containers:
        return containers[0].get("image", "unknown")
    return "unknown"


def get_service_ports(resource: Dict[str, Any]) -> str:
    """Extract ports from service spec."""
    ports = resource.get("spec", {}).get("ports", [])
    return ", ".join([str(p.get("port")) for p in ports[:3]])


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
