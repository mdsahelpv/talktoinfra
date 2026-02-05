"""
RAG Service - Retrieval-Augmented Generation for Infrastructure

This service provides semantic search and retrieval capabilities
for infrastructure data using vector embeddings.
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1 import index, search, sources
from config import get_settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.make_filtering_bound_logger(logging.INFO),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()

    logger.info(
        "rag_service_starting",
        service=settings.service_name,
        port=settings.service_port,
        debug=settings.debug,
    )

    # Initialize services
    try:
        from services.indexer import get_indexer
        indexer = get_indexer()

        # Ensure default collections exist
        collections = [
            settings.collection_infrastructure,
            settings.collection_logs,
            settings.collection_docs,
            settings.collection_k8s_resources,
        ]

        for collection in collections:
            await indexer.ensure_collection(collection)
            logger.info("collection_ready", collection=collection)

    except Exception as e:
        logger.warning("service_initialization_warning", error=str(e))

    yield

    # Shutdown
    logger.info("rag_service_stopping")


# Create FastAPI application
app = FastAPI(
    title="TalkAI RAG Service",
    description="Retrieval-Augmented Generation for Infrastructure Data",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include API routers
app.include_router(index.router, prefix="/api/v1/rag")
app.include_router(search.router, prefix="/api/v1/rag")
app.include_router(sources.router, prefix="/api/v1/rag")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "rag-service"}


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "TalkAI RAG Service",
        "version": "1.0.0",
        "description": "Retrieval-Augmented Generation for Infrastructure",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1/rag",
        },
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
    )
