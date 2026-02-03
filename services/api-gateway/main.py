"""
API Gateway Service
Entry point for all client requests. Handles:
- Authentication and authorization
- Rate limiting
- Request routing to backend services
- WebSocket connections for real-time updates
- Audit logging of all requests
"""

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import httpx
import structlog
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from auth import verify_token, create_token
from models import (
    QueryRequest,
    QueryResponse,
    ActionRequest,
    ActionResponse,
    UserLogin,
)
from config import Settings, get_settings

# Configure logging
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
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# HTTP clients for backend services
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global http_client

    # Startup
    settings = get_settings()
    http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    )
    logger.info("api_gateway_starting", port=settings.service_port)

    yield

    # Shutdown
    await http_client.aclose()
    logger.info("api_gateway_stopping")


app = FastAPI(
    title="AI Infrastructure Operations - API Gateway",
    description="Entry point for all client requests with auth, rate limiting, and routing",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect metrics for all requests."""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    REQUEST_DURATION.labels(method=request.method, endpoint=request.url.path).observe(
        duration
    )

    REQUEST_COUNT.labels(
        method=request.method, endpoint=request.url.path, status=response.status_code
    ).inc()

    # Add request ID header
    response.headers["X-Request-ID"] = str(uuid.uuid4())

    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests with context."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    bind_context = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client": request.client.host if request.client else None,
    }

    structlog.contextvars.bind_contextvars(**bind_context)
    logger.info("request_started")

    try:
        response = await call_next(request)
        logger.info("request_completed", status_code=response.status_code)
        return response
    except Exception as e:
        logger.error("request_failed", error=str(e))
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "timestamp": time.time(),
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return JSONResponse(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Authentication Endpoints


@app.post("/auth/login", response_model=dict)
@limiter.limit("100/minute")
async def login(
    request: Request, credentials: UserLogin, settings: Settings = Depends(get_settings)
):
    """Authenticate user and return JWT token."""
    # TODO: Implement actual authentication against user service
    # For now, simple check against configured credentials

    if (
        credentials.username == "admin"
        and credentials.password == settings.admin_password
    ):
        token = create_token(
            user_id="admin",
            username=credentials.username,
            roles=["admin"],
            secret=settings.jwt_secret,
        )
        logger.info("user_logged_in", username=credentials.username)
        return {"access_token": token, "token_type": "bearer"}

    logger.warning("login_failed", username=credentials.username)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
    )


@app.post("/auth/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Refresh JWT token."""
    token = credentials.credentials
    payload = verify_token(token, settings.jwt_secret)

    new_token = create_token(
        user_id=payload["sub"],
        username=payload.get("username", ""),
        roles=payload.get("roles", []),
        secret=settings.jwt_secret,
    )

    return {"access_token": new_token, "token_type": "bearer"}


@app.get("/auth/me")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get current authenticated user info."""
    token = credentials.credentials
    payload = verify_token(token, settings.jwt_secret)

    return {
        "id": payload["sub"],
        "username": payload.get("username", ""),
        "roles": payload.get("roles", []),
    }


# Query Endpoints


@app.post("/api/v1/query", response_model=QueryResponse)
@limiter.limit("100/minute")
async def submit_query(
    request: Request,
    query: QueryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Submit a natural language query to the AI Router."""
    # Verify token
    payload = verify_token(credentials.credentials, settings.jwt_secret)
    user_id = payload["sub"]

    # Forward to AI Router
    try:
        response = await http_client.post(
            f"{settings.ai_router_url}/query",
            json={
                "query": query.query,
                "conversation_id": query.conversation_id,
                "context": query.context,
                "user_id": user_id,
            },
            headers={"X-Request-ID": request.state.request_id},
        )
        response.raise_for_status()
        data = response.json()

        logger.info(
            "query_processed",
            query=query.query[:50],
            user_id=user_id,
            intent=data.get("intent"),
        )

        return QueryResponse(
            response=data["response"],
            conversation_id=data["conversation_id"],
            sources=data.get("sources", []),
            metadata=data.get("metadata", {}),
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "ai_router_error", status_code=e.response.status_code, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="AI Router service error"
        )
    except Exception as e:
        logger.error("query_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process query",
        )


# Action Endpoints


@app.post("/api/v1/actions/dry-run", response_model=ActionResponse)
@limiter.limit("50/minute")
async def dry_run_action(
    request: Request,
    action: ActionRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Execute action in dry-run mode."""
    payload = verify_token(credentials.credentials, settings.jwt_secret)
    user_id = payload["sub"]

    try:
        response = await http_client.post(
            f"{settings.action_engine_url}/actions/dry-run",
            json={
                "action": action.action,
                "target": action.target,
                "parameters": action.parameters,
                "user_id": user_id,
                "user_roles": payload.get("roles", []),
            },
            headers={"X-Request-ID": request.state.request_id},
        )
        response.raise_for_status()
        data = response.json()

        return ActionResponse(
            action_id=data["action_id"],
            status=data["status"],
            dry_run_result=data.get("dry_run_result"),
            requires_approval=data.get("requires_approval", False),
            approvers=data.get("approvers", []),
        )
    except Exception as e:
        logger.error("dry_run_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute dry-run",
        )


@app.post("/api/v1/actions/execute", response_model=ActionResponse)
@limiter.limit("20/minute")
async def execute_action(
    request: Request,
    action_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Execute an approved action."""
    payload = verify_token(credentials.credentials, settings.jwt_secret)
    user_id = payload["sub"]

    try:
        response = await http_client.post(
            f"{settings.action_engine_url}/actions/execute",
            json={
                "action_id": action_id,
                "user_id": user_id,
                "user_roles": payload.get("roles", []),
            },
            headers={"X-Request-ID": request.state.request_id},
        )
        response.raise_for_status()
        return ActionResponse(**response.json())
    except Exception as e:
        logger.error("action_execution_failed", error=str(e), action_id=action_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute action",
        )


# Approval Endpoints


@app.get("/api/v1/approvals/pending")
async def get_pending_approvals(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get pending approvals for the current user."""
    payload = verify_token(credentials.credentials, settings.jwt_secret)
    user_id = payload["sub"]

    try:
        response = await http_client.get(
            f"{settings.policy_engine_url}/approvals/pending",
            params={"user_id": user_id, "roles": payload.get("roles", [])},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error("fetch_approvals_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch approvals",
        )


@app.post("/api/v1/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Approve a pending action."""
    payload = verify_token(credentials.credentials, settings.jwt_secret)
    user_id = payload["sub"]

    try:
        response = await http_client.post(
            f"{settings.policy_engine_url}/approvals/{approval_id}/approve",
            json={"user_id": user_id},
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            raise HTTPException(status_code=403, detail="Not authorized to approve")
        raise HTTPException(status_code=500, detail="Failed to process approval")


# WebSocket for Real-time Updates


@app.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: str):
    """WebSocket for real-time chat updates."""
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Process through AI Router
            response = await http_client.post(
                f"{get_settings().ai_router_url}/query/stream",
                json={
                    "query": data.get("query"),
                    "conversation_id": conversation_id,
                    "context": data.get("context"),
                },
            )

            # Stream response back
            async for chunk in response.aiter_text():
                await websocket.send_text(chunk)

    except WebSocketDisconnect:
        logger.info("websocket_disconnected", conversation_id=conversation_id)
    except Exception as e:
        logger.error("websocket_error", error=str(e), conversation_id=conversation_id)
        await websocket.close()


@app.get("/api/v1/infra", response_model=dict)
@limiter.limit("100/minute")
async def get_infrastructure(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get infrastructure details from real services.

    Queries the onboarding service for registered clusters and
    discovery service for managed hosts. No mock data is returned.
    """
    token = credentials.credentials
    payload = verify_token(token, settings.jwt_secret)

    # Query clusters from onboarding service
    clusters = []
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = await http_client.get(
            f"{settings.onboarding_service_url}/api/v1/clusters",
            headers=headers,
            timeout=10.0,
        )
        if response.status_code == 200:
            clusters_data = response.json()
            clusters = clusters_data.get("clusters", [])
    except httpx.RequestError as e:
        logger.warning("onboarding_service_unavailable", error=str(e))
    except Exception as e:
        logger.error("clusters_query_failed", error=str(e))

    # Query managed hosts from discovery service
    hosts = []
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = await http_client.get(
            f"{settings.discovery_service_url}/api/v1/hosts",
            headers=headers,
            timeout=10.0,
        )
        if response.status_code == 200:
            hosts_data = response.json()
            hosts = hosts_data.get("hosts", [])
    except httpx.RequestError as e:
        logger.warning("discovery_service_unavailable", error=str(e))
    except Exception as e:
        logger.error("hosts_query_failed", error=str(e))

    # Build response with real data only
    infra_data = {
        "clusters": clusters,
        "hosts": hosts,
        "summary": {
            "total_clusters": len(clusters),
            "total_hosts": len(hosts),
            "last_updated": datetime.utcnow().isoformat() + "Z",
        },
    }

    logger.info(
        "infrastructure_queried",
        username=payload.get("username"),
        clusters_count=len(clusters),
        hosts_count=len(hosts),
    )
    return infra_data


# Infrastructure Discovery Endpoints


@app.get("/api/v1/scan/presets")
async def get_scan_presets(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get list of available port scan presets."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/scan/presets",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.post("/api/v1/scan/start")
@limiter.limit("1/minute")
async def start_network_scan(
    request: Request,
    scan_request: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Start a new network scan job."""
    token = credentials.credentials
    payload = verify_token(token, settings.jwt_secret)

    # TODO: Implement proper authorization in future
    # Currently all authenticated users can run network scans
    # roles = payload.get("roles", [])
    # if "admin" not in roles:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only administrators can run network scans",
    #     )

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.post(
            f"{discovery_url}/api/v1/scans",
            json=scan_request,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.get("/api/v1/scan/{job_id}/status")
async def get_scan_status(
    job_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get status of a scan job."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/scans/{job_id}/status",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.get("/api/v1/scan/{job_id}/results")
async def get_scan_results(
    job_id: str,
    alive_only: bool = True,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get results of a scan job."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/scans/{job_id}/results",
            params={"alive_only": alive_only},
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.post("/api/v1/scan/{job_id}/stop")
async def stop_scan(
    job_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Stop a running scan job."""
    token = credentials.credentials
    payload = verify_token(token, settings.jwt_secret)

    # TODO: Implement proper authorization in future
    # Currently all authenticated users can stop scans
    # roles = payload.get("roles", [])
    # if "admin" not in roles:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only administrators can stop scans",
    #     )

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.post(
            f"{discovery_url}/api/v1/scans/{job_id}/stop",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.get("/api/v1/discovery/port-presets")
async def get_discovery_port_presets(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get list of available port scan presets."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/scan/presets",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.get("/api/v1/discovery/scans")
async def get_discovery_scans(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get list of discovery scans with optional filtering."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    params = {}
    if status:
        params["status"] = status
    params["limit"] = limit
    params["offset"] = offset

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/discovery/scans",
            params=params,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.post("/api/v1/discovery/scans")
@limiter.limit("1/minute")
async def create_discovery_scan(
    request: Request,
    scan_request: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Create a new discovery scan."""
    token = credentials.credentials
    payload = verify_token(token, settings.jwt_secret)

    # TODO: Implement proper authorization in future
    # Currently all authenticated users can create scans
    # roles = payload.get("roles", [])
    # if "admin" not in roles:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only administrators can create scans",
    #     )

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.post(
            f"{discovery_url}/api/v1/discovery/scans",
            json=scan_request,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.get("/api/v1/discovery/scans/{scan_id}")
async def get_discovery_scan(
    scan_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get details of a specific discovery scan."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/discovery/scans/{scan_id}",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.get("/api/v1/discovery/scans/{scan_id}/status")
async def get_discovery_scan_status(
    scan_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get status of a specific discovery scan."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/discovery/scans/{scan_id}/status",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.get("/api/v1/discovery/scans/{scan_id}/results")
async def get_discovery_scan_results(
    scan_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get results of a specific discovery scan."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/discovery/scans/{scan_id}/results",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.post("/api/v1/discovery/scans/{scan_id}/stop")
async def stop_discovery_scan(
    scan_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Stop a running discovery scan."""
    token = credentials.credentials
    payload = verify_token(token, settings.jwt_secret)

    # TODO: Implement proper authorization in future
    # Currently all authenticated users can stop discovery scans
    # roles = payload.get("roles", [])
    # if "admin" not in roles:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only administrators can stop scans",
    #     )

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.post(
            f"{discovery_url}/api/v1/discovery/scans/{scan_id}/stop",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.delete("/api/v1/discovery/scans/{scan_id}")
async def delete_discovery_scan(
    scan_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Delete a discovery scan."""
    token = credentials.credentials
    payload = verify_token(token, settings.jwt_secret)

    # TODO: Implement proper authorization in future
    # Currently all authenticated users can delete discovery scans
    # roles = payload.get("roles", [])
    # if "admin" not in roles:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only administrators can delete scans",
    #     )

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.delete(
            f"{discovery_url}/api/v1/discovery/scans/{scan_id}",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.get("/api/v1/discovery/scanners")
async def get_discovery_scanners(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get list of available discovery scanners."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/discovery/scanners",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.get("/api/v1/discovery/status")
async def get_discovery_status(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Get discovery service status."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/discovery/status",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.get("/api/v1/hosts")
async def list_managed_hosts(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """List all managed infrastructure hosts."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.get(
            f"{discovery_url}/api/v1/hosts",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


@app.post("/api/v1/hosts")
async def add_managed_host(
    host_request: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
):
    """Add a new managed host."""
    token = credentials.credentials
    verify_token(token, settings.jwt_secret)

    headers = {"Authorization": f"Bearer {token}"}
    discovery_url = settings.discovery_service_url

    try:
        response = await http_client.post(
            f"{discovery_url}/api/v1/hosts",
            json=host_request,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Discovery service error: {e.response.text}",
        )
    except httpx.RequestError as e:
        logger.error("discovery_service_unavailable", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Discovery service unavailable",
        )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
