import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.router import api_router
from src.api.ws.chat import chat_ws_router
from src.storage.database import create_db_and_tables

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()

    # -- Enterprise Phase 1a: OIDC --
    if settings.auth_oidc_issuer:
        from src.auth.oidc import OIDCProvider
        app.state.oidc_provider = OIDCProvider()
        logger.info("OIDC provider initialized (issuer=%s)", settings.auth_oidc_issuer)
    else:
        app.state.oidc_provider = None

    # -- Enterprise Phase 1: SAML provider --
    from src.auth.saml import saml_provider
    app.state.saml_provider = saml_provider

    # -- Enterprise Phase 1: Agent identity manager --
    from src.auth.agent_identity import agent_identity_manager
    app.state.agent_identity_manager = agent_identity_manager

    # -- Enterprise Phase 2: SIEM exporter --
    from src.observability.siem import CompositeExporter, WebhookExporter, SyslogExporter
    exporters = []
    if settings.siem_webhook_url:
        exporters.append(WebhookExporter(settings.siem_webhook_url))
    if settings.siem_syslog_host:
        exporters.append(SyslogExporter(settings.siem_syslog_host, settings.siem_syslog_port))
    app.state.siem_exporter = CompositeExporter(exporters) if exporters else None

    # -- Enterprise Phase 2: OpenTelemetry tracing --
    if settings.otel_exporter_endpoint:
        from src.observability.tracing import setup_tracing
        setup_tracing(settings.otel_service_name, settings.otel_exporter_endpoint)
        logger.info("OpenTelemetry tracing initialized")

    # -- Enterprise Phase 2: Cost tracker --
    from src.observability.cost_tracker import CostTracker
    app.state.cost_tracker = CostTracker()

    # -- Enterprise Phase 2: Heartbeat monitor --
    from src.observability.heartbeat import HeartbeatMonitor
    app.state.heartbeat_monitor = HeartbeatMonitor()
    logger.info("Heartbeat monitor initialized (SLA=%ds)", settings.heartbeat_sla_seconds)

    # -- Enterprise Phase 5c: Air-gapped verification --
    if settings.air_gapped:
        logger.warning("Running in AIR-GAPPED mode — only local LLM providers allowed")
        if settings.openai_api_key or settings.anthropic_api_key:
            logger.warning("Air-gapped mode: external API keys configured but will be ignored")

    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Enterprise Phase 6c: Rate limiting middleware --
from src.api.ratelimit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# -- Enterprise Phase 6b: API versioning middleware --
from src.api.versioning import APIVersionMiddleware
app.add_middleware(APIVersionMiddleware)

app.include_router(api_router, prefix="/api/v1")
app.include_router(chat_ws_router)


@app.get("/health")
async def health():
    return {
        "service": "talktoinfra-orchestrator",
        "version": settings.app_version,
        "healthy": True,
    }
