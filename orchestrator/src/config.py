from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "TalkToInfra Orchestrator"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "*"

    # LLM Providers
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    default_llm_provider: str = "openai"

    # Agent
    agent_grpc_host: str = "localhost"
    agent_grpc_port: int = 9000
    agent_max_iterations: int = 20
    agent_read_timeout: int = 60

    # Safety
    safety_destructive_require_reason: bool = True
    safety_approval_timeout_seconds: int = 300

    # Storage
    database_url: str = "sqlite+aiosqlite:///./data/talktoinfra.db"
    vector_store_type: str = "chroma"
    vector_store_path: str = "./data/vectors"

    # Auth (enterprise: JWT + OIDC + API key fallback)
    api_keys: str = ""  # comma-separated
    enable_auth: bool = False
    auth_jwt_secret: str = "change-me-in-production"
    auth_jwt_expiry_hours: int = 1
    auth_oidc_issuer: str = ""
    auth_oidc_audience: str = ""
    auth_oidc_jwks_url: str = ""
    auth_oidc_org_field: str = "org_id,org,tenant_id"

    # -- Enterprise Phase 1: SAML --
    auth_saml_metadata_url: str = ""
    auth_saml_entity_id: str = "talktoinfra-orchestrator"
    auth_saml_acs_url: str = ""

    # -- Enterprise Phase 1: MFA --
    auth_mfa_required: bool = False
    auth_mfa_issuer: str = "TalkToInfra"

    # -- Enterprise Phase 2: SIEM --
    siem_webhook_url: str = ""
    siem_syslog_host: str = ""
    siem_syslog_port: int = 514
    siem_export_interval_seconds: int = 60

    # -- Enterprise Phase 2: OpenTelemetry --
    otel_exporter_endpoint: str = ""
    otel_service_name: str = "talktoinfra-orchestrator"

    # -- Enterprise Phase 2: Cost tracking --
    cost_budget_per_org: float = 0
    cost_alert_threshold: float = 0.8

    # -- Enterprise Phase 2: Heartbeat SLA --
    heartbeat_sla_seconds: int = 30

    # -- Enterprise Phase 3: Approval backends --
    approval_backend: str = "webhook"
    approval_slack_webhook_url: str = ""
    approval_slack_channel: str = ""
    approval_email_smtp_host: str = ""
    approval_email_from: str = ""

    # -- Enterprise Phase 4: Checkpointing --
    checkpoint_db_url: str = ""

    # -- Enterprise Phase 4: Multi-region --
    deploy_regions: str = ""
    deploy_primary_region: str = "us-east"

    # -- Enterprise Phase 5: Data residency & air-gap --
    data_residency_region: str = "auto"
    air_gapped: bool = False

    # -- Enterprise Phase 6: API versioning & rate limits --
    api_supported_versions: str = "1.0"
    api_sunset_versions: str = ""
    rate_limit_per_user: int = 100
    rate_limit_per_org: int = 1000
    rate_limit_global: int = 10000

    # Knowledge
    knowledge_embedding_model: str = "all-MiniLM-L6-v2"

    model_config = {"env_prefix": "TALKTOINFRA_", "env_file": ".env"}


settings = Settings()
