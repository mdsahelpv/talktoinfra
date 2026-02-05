"""
Model registry and management service.

Model registry singleton
Provider management
Model selection logic
Fallback chain execution
Cost tracking per request
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog

from models_config import (
    ProviderType,
    ModelCapability,
    ModelCost,
    ProviderConfig,
    ModelConfig,
    FallbackChain,
    CostTrackingEntry,
    ProviderCredentials,
    ModelRegistry,
    ModelUsageStats,
)

logger = structlog.get_logger()


class ModelRegistryService:
    """Model registry singleton for managing AI models and providers."""

    _instance: Optional["ModelRegistryService"] = None

    def __new__(cls) -> "ModelRegistryService":
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the model registry service."""
        if self._initialized:
            return

        self.registry = ModelRegistry()
        self.credentials: Dict[str, ProviderCredentials] = {}
        self.usage_stats: Dict[str, ModelUsageStats] = {}
        self.cost_history: List[CostTrackingEntry] = []
        self._load_default_config()
        self._initialized = True
        logger.info("model_registry_initialized")

    def _load_default_config(self) -> None:
        """Load default provider and model configurations."""
        # Ollama Provider
        ollama_provider = ProviderConfig(
            id="ollama-default",
            name="Ollama Local",
            provider_type=ProviderType.OLLAMA,
            enabled=True,
            base_url="http://localhost:11434",
            capabilities=[
                ModelCapability.CHAT,
                ModelCapability.COMPLETION,
                ModelCapability.CODE,
            ],
            cost=ModelCost(input_cost_per_token=0.0, output_cost_per_token=0.0),
        )
        self.registry.providers["ollama-default"] = ollama_provider

        # Ollama Models
        ollama_models = [
            ModelConfig(
                id="llama3.3:70b",
                name="Llama 3.3 70B",
                provider_id="ollama-default",
                model_id="llama3.3:70b",
                enabled=True,
                capabilities=[ModelCapability.CHAT, ModelCapability.REASONING],
                context_length=131072,
                description="Meta Llama 3.3 70B Instruct",
            ),
            ModelConfig(
                id="codellama:34b",
                name="Code Llama 34B",
                provider_id="ollama-default",
                model_id="codellama:34b",
                enabled=True,
                capabilities=[ModelCapability.CODE, ModelCapability.CHAT],
                context_length=131072,
                description="Meta Code Llama 34B Instruct",
            ),
            ModelConfig(
                id="nomic-embed-text",
                name="Nomic Embed Text",
                provider_id="ollama-default",
                model_id="nomic-embed-text",
                enabled=True,
                capabilities=[ModelCapability.EMBEDDING],
                context_length=8192,
                description="Nomic embedding model",
            ),
        ]
        for model in ollama_models:
            self.registry.models[model.id] = model

        # OpenAI Provider (disabled by default without API key)
        openai_provider = ProviderConfig(
            id="openai-default",
            name="OpenAI",
            provider_type=ProviderType.OPENAI,
            enabled=False,
            base_url="https://api.openai.com/v1",
            capabilities=[
                ModelCapability.CHAT,
                ModelCapability.COMPLETION,
                ModelCapability.EMBEDDING,
            ],
            rate_limit_rpm=60,
        )
        self.registry.providers["openai-default"] = openai_provider

        # Set default model assignments
        self.registry.default_model_for_capability = {
            "chat": "llama3.3:70b",
            "code": "codellama:34b",
            "embedding": "nomic-embed-text",
            "reasoning": "llama3.3:70b",
        }

        # Default fallback chain
        fallback_chain = FallbackChain(
            id="default-chain",
            name="Default Fallback",
            description="Default fallback chain for reliability",
            models=["llama3.3:70b"],
            enabled=True,
            retry_count=1,
            timeout_per_model_ms=30000,
        )
        self.registry.fallback_chains["default-chain"] = fallback_chain

    # Provider Management
    def add_provider(self, provider: ProviderConfig) -> None:
        """Add a new provider to the registry."""
        self.registry.providers[provider.id] = provider
        logger.info("provider_added", provider_id=provider.id, name=provider.name)

    def get_provider(self, provider_id: str) -> Optional[ProviderConfig]:
        """Get a provider by ID."""
        return self.registry.providers.get(provider_id)

    def list_providers(self, enabled_only: bool = False) -> List[ProviderConfig]:
        """List all providers."""
        providers = list(self.registry.providers.values())
        if enabled_only:
            providers = [p for p in providers if p.enabled]
        return providers

    def update_provider(
        self, provider_id: str, updates: Dict[str, Any]
    ) -> Optional[ProviderConfig]:
        """Update a provider configuration."""
        provider = self.registry.providers.get(provider_id)
        if not provider:
            return None

        for key, value in updates.items():
            if hasattr(provider, key):
                setattr(provider, key, value)

        logger.info("provider_updated", provider_id=provider_id)
        return provider

    def delete_provider(self, provider_id: str) -> bool:
        """Delete a provider from the registry."""
        if provider_id not in self.registry.providers:
            return False

        # Check if any models are using this provider
        for model in self.registry.models.values():
            if model.provider_id == provider_id:
                logger.warning(
                    "provider_has_models",
                    provider_id=provider_id,
                    model_id=model.id,
                )

        del self.registry.providers[provider_id]
        logger.info("provider_deleted", provider_id=provider_id)
        return True

    # Model Management
    def add_model(self, model: ModelConfig) -> None:
        """Add a new model to the registry."""
        self.registry.models[model.id] = model
        logger.info("model_added", model_id=model.id, name=model.name)

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get a model by ID."""
        return self.registry.models.get(model_id)

    def list_models(
        self,
        provider_id: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
    ) -> List[ModelConfig]:
        """List models with optional filtering."""
        models = list(self.registry.models.values())

        if provider_id:
            models = [m for m in models if m.provider_id == provider_id]

        if capabilities:
            capability_enums = [ModelCapability(c) for c in capabilities]
            models = [
                m
                for m in models
                if any(cap in m.capabilities for cap in capability_enums)
            ]

        return [m for m in models if m.enabled]

    def update_model(
        self, model_id: str, updates: Dict[str, Any]
    ) -> Optional[ModelConfig]:
        """Update a model configuration."""
        model = self.registry.models.get(model_id)
        if not model:
            return None

        for key, value in updates.items():
            if hasattr(model, key):
                setattr(model, key, value)

        logger.info("model_updated", model_id=model_id)
        return model

    def delete_model(self, model_id: str) -> bool:
        """Delete a model from the registry."""
        if model_id not in self.registry.models:
            return False

        del self.registry.models[model_id]
        logger.info("model_deleted", model_id=model_id)
        return True

    # Model Selection Logic
    def select_model(
        self,
        capability: str,
        fallback_chain: Optional[str] = None,
        prefer_fast: bool = False,
    ) -> Optional[ModelConfig]:
        """Select the best model for a given capability."""
        capability_enum = ModelCapability(capability)
        candidates = self.list_models(capabilities=[capability])

        if not candidates:
            # Try default model for capability
            default_model_id = self.registry.default_model_for_capability.get(
                capability
            )
            if default_model_id:
                return self.get_model(default_model_id)
            return None

        # Sort by preference
        candidates.sort(key=lambda m: (0 if not prefer_fast else 1, m.id))

        if fallback_chain:
            chain = self.registry.fallback_chains.get(fallback_chain)
            if chain:
                for model_id in chain.models:
                    model = self.get_model(model_id)
                    if model and capability_enum in model.capabilities:
                        return model

        return candidates[0] if candidates else None

    # Fallback Chain Management
    def add_fallback_chain(self, chain: FallbackChain) -> None:
        """Add a new fallback chain."""
        self.registry.fallback_chains[chain.id] = chain
        logger.info("fallback_chain_added", chain_id=chain.id, name=chain.name)

    def get_fallback_chain(self, chain_id: str) -> Optional[FallbackChain]:
        """Get a fallback chain by ID."""
        return self.registry.fallback_chains.get(chain_id)

    def list_fallback_chains(self) -> List[FallbackChain]:
        """List all fallback chains."""
        return list(self.registry.fallback_chains.values())

    # Cost Tracking
    def track_cost(self, entry: CostTrackingEntry) -> None:
        """Track cost for a single request."""
        self.cost_history.append(entry)

        # Update usage stats
        if entry.model_id not in self.usage_stats:
            self.usage_stats[entry.model_id] = ModelUsageStats(model_id=entry.model_id)

        stats = self.usage_stats[entry.model_id]
        stats.total_requests += 1
        stats.total_input_tokens += entry.input_tokens
        stats.total_output_tokens += entry.output_tokens
        stats.total_cost += entry.total_cost
        stats.last_used = datetime.utcnow()

        logger.info(
            "cost_tracked",
            request_id=entry.request_id,
            model_id=entry.model_id,
            cost=entry.total_cost,
        )

    def calculate_request_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Tuple[float, float]:
        """Calculate cost for a request."""
        model = self.get_model(model_id)
        if not model:
            return 0.0, 0.0

        input_cost = input_tokens * model.cost.input_cost_per_token
        output_cost = output_tokens * model.cost.output_cost_per_token
        return input_cost, output_cost

    def get_cost_summary(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get cost summary for a time period."""
        entries = self.cost_history

        if start_date:
            entries = [e for e in entries if e.timestamp >= start_date]
        if end_date:
            entries = [e for e in entries if e.timestamp <= end_date]

        total_cost = sum(e.total_cost for e in entries)
        total_input_tokens = sum(e.input_tokens for e in entries)
        total_output_tokens = sum(e.output_tokens for e in entries)
        total_requests = len(entries)

        by_model = {}
        for entry in entries:
            if entry.model_id not in by_model:
                by_model[entry.model_id] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                }
            by_model[entry.model_id]["requests"] += 1
            by_model[entry.model_id]["input_tokens"] += entry.input_tokens
            by_model[entry.model_id]["output_tokens"] += entry.output_tokens
            by_model[entry.model_id]["cost"] += entry.total_cost

        return {
            "total_requests": total_requests,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cost": total_cost,
            "currency": "USD",
            "by_model": by_model,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
        }

    def get_usage_stats(self, model_id: Optional[str] = None) -> List[ModelUsageStats]:
        """Get usage statistics."""
        if model_id:
            return (
                [self.usage_stats.get(model_id)] if model_id in self.usage_stats else []
            )

        return list(self.usage_stats.values())

    # Credentials Management
    def set_credentials(self, credentials: ProviderCredentials) -> None:
        """Set provider credentials."""
        self.credentials[credentials.provider_id] = credentials
        logger.info("credentials_set", provider_id=credentials.provider_id)

    def get_credentials(self, provider_id: str) -> Optional[ProviderCredentials]:
        """Get provider credentials."""
        return self.credentials.get(provider_id)

    def delete_credentials(self, provider_id: str) -> bool:
        """Delete provider credentials."""
        if provider_id in self.credentials:
            del self.credentials[provider_id]
            logger.info("credentials_deleted", provider_id=provider_id)
            return True
        return False

    # Registry Export/Import
    def export_registry(self) -> Dict[str, Any]:
        """Export registry configuration."""
        return {
            "providers": {
                k: v.model_dump() for k, v in self.registry.providers.items()
            },
            "models": {k: v.model_dump() for k, v in self.registry.models.items()},
            "fallback_chains": {
                k: v.model_dump() for k, v in self.registry.fallback_chains.items()
            },
            "default_model_for_capability": self.registry.default_model_for_capability,
            "cost_tracking_enabled": self.registry.cost_tracking_enabled,
            "budget_limit_monthly": self.registry.budget_limit_monthly,
        }

    def import_registry(self, data: Dict[str, Any]) -> None:
        """Import registry configuration."""
        self.registry = ModelRegistry(**data)


def get_model_registry() -> ModelRegistryService:
    """Get the model registry singleton instance."""
    return ModelRegistryService()
