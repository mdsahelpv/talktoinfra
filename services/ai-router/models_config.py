"""
Model configurations for AI Router.

Provider configurations (OpenAI, Anthropic, Azure, Bedrock, Ollama, vLLM)
Model settings (temperature, max_tokens, top_p, frequency_penalty, presence_penalty)
Fallback chain configuration
Model cost tracking per request
Provider credentials management (API keys, endpoints)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """AI provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    BEDROCK = "bedrock"
    OLLAMA = "ollama"
    VLLM = "vllm"


class ModelCapability(str, Enum):
    """Model capabilities."""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    CODE = "code"
    REASONING = "reasoning"
    MULTIMODAL = "multimodal"


class ModelCost(BaseModel):
    """Model cost per 1K tokens."""

    input_cost_per_token: float = Field(default=0.0, description="Cost per input token")
    output_cost_per_token: float = Field(
        default=0.0, description="Cost per output token"
    )
    currency: str = Field(default="USD", description="Currency code")


class ModelSettings(BaseModel):
    """Model generation settings."""

    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Temperature for sampling"
    )
    max_tokens: int = Field(
        default=4096, ge=1, description="Maximum tokens to generate"
    )
    top_p: float = Field(default=0.95, ge=0.0, le=1.0, description="Top-p sampling")
    frequency_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: float = Field(
        default=0.0, ge=-2.0, le=2.0, description="Presence penalty"
    )
    stop_sequences: List[str] = Field(
        default_factory=list, description="Stop sequences"
    )


class ProviderConfig(BaseModel):
    """Provider configuration."""

    id: str = Field(..., description="Provider unique identifier")
    name: str = Field(..., description="Provider display name")
    provider_type: ProviderType = Field(..., description="Provider type")
    enabled: bool = Field(default=True, description="Provider enabled status")
    base_url: Optional[str] = Field(None, description="API base URL")
    api_key: Optional[str] = Field(
        None, description="API key (should be stored securely)"
    )
    api_version: Optional[str] = Field(None, description="API version (for Azure)")
    region: Optional[str] = Field(None, description="Region (for AWS/Azure)")
    model_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Model ID mappings"
    )
    timeout_seconds: int = Field(default=60, description="Request timeout")
    rate_limit_rpm: Optional[int] = Field(None, description="Rate limit per minute")
    rate_limit_tpm: Optional[int] = Field(
        None, description="Rate limit tokens per minute"
    )
    capabilities: List[ModelCapability] = Field(
        default_factory=list, description="Provider capabilities"
    )
    cost: ModelCost = Field(
        default_factory=ModelCost, description="Default cost settings"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ModelConfig(BaseModel):
    """Model configuration."""

    id: str = Field(..., description="Model unique identifier")
    name: str = Field(..., description="Model display name")
    provider_id: str = Field(..., description="Associated provider")
    model_id: str = Field(..., description="Provider's model identifier")
    enabled: bool = Field(default=True, description="Model enabled status")
    capabilities: List[ModelCapability] = Field(
        default_factory=list, description="Model capabilities"
    )
    settings: ModelSettings = Field(
        default_factory=ModelSettings, description="Model settings"
    )
    cost: ModelCost = Field(
        default_factory=ModelCost, description="Model cost settings"
    )
    context_length: int = Field(default=4096, description="Maximum context length")
    description: Optional[str] = Field(None, description="Model description")
    version: str = Field(default="1.0.0", description="Model version")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class FallbackChain(BaseModel):
    """Model fallback chain configuration."""

    id: str = Field(..., description="Fallback chain identifier")
    name: str = Field(..., description="Chain display name")
    description: Optional[str] = Field(None, description="Chain description")
    models: List[str] = Field(..., description="Model IDs in fallback order")
    enabled: bool = Field(default=True, description="Chain enabled status")
    retry_count: int = Field(default=1, description="Retries per model")
    timeout_per_model_ms: int = Field(
        default=30000, description="Timeout per model in ms"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class CostTrackingEntry(BaseModel):
    """Cost tracking entry for a single request."""

    request_id: str = Field(..., description="Request unique identifier")
    provider_id: str = Field(..., description="Provider used")
    model_id: str = Field(..., description="Model used")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")
    input_cost: float = Field(default=0.0, description="Cost for input tokens")
    output_cost: float = Field(default=0.0, description="Cost for output tokens")
    total_cost: float = Field(default=0.0, description="Total cost")
    currency: str = Field(default="USD", description="Currency")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Request timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ProviderCredentials(BaseModel):
    """Provider credentials management."""

    provider_id: str = Field(..., description="Provider identifier")
    api_key: Optional[str] = Field(None, description="API key")
    api_secret: Optional[str] = Field(None, description="API secret")
    session_token: Optional[str] = Field(None, description="Session token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    token_expiry: Optional[datetime] = Field(None, description="Token expiry time")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ModelRegistry(BaseModel):
    """Complete model registry configuration."""

    providers: Dict[str, ProviderConfig] = Field(
        default_factory=dict, description="Providers"
    )
    models: Dict[str, ModelConfig] = Field(default_factory=dict, description="Models")
    fallback_chains: Dict[str, FallbackChain] = Field(
        default_factory=dict, description="Fallback chains"
    )
    default_model_for_capability: Dict[str, str] = Field(
        default_factory=dict, description="Default model per capability"
    )
    cost_tracking_enabled: bool = Field(
        default=True, description="Cost tracking enabled"
    )
    budget_limit_monthly: Optional[float] = Field(
        None, description="Monthly budget limit"
    )


class ModelUsageStats(BaseModel):
    """Model usage statistics."""

    model_id: str = Field(..., description="Model identifier")
    total_requests: int = Field(default=0, description="Total requests")
    total_input_tokens: int = Field(default=0, description="Total input tokens")
    total_output_tokens: int = Field(default=0, description="Total output tokens")
    total_cost: float = Field(default=0.0, description="Total cost")
    avg_response_time_ms: float = Field(
        default=0.0, description="Average response time"
    )
    success_rate: float = Field(default=0.0, description="Success rate")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
