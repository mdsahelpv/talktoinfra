"""LLM Provider registry."""

import logging

from src.config import settings
from src.llm.provider import LLMProvider
from src.llm.openai_provider import OpenAIProvider
from src.llm.anthropic_provider import AnthropicProvider
from src.llm.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


class LLMRegistry:
    _providers: dict[str, LLMProvider] = {}

    @classmethod
    def register(cls, name: str, provider: LLMProvider) -> None:
        cls._providers[name] = provider

    @classmethod
    def get_provider(cls, name: str) -> LLMProvider:
        if not cls._providers:
            cls._register_defaults()
        # -- Enterprise Phase 5c: air-gapped mode --
        if settings.air_gapped and name not in ("ollama",):
            logger.warning("Air-gapped mode: rejecting non-local provider '%s', falling back to ollama", name)
            name = "ollama"
        provider = cls._providers.get(name)
        if not provider:
            raise ValueError(f"Unknown LLM provider: {name}. Available: {list(cls._providers.keys())}")
        return provider

    @classmethod
    def list_providers(cls) -> list[str]:
        if not cls._providers:
            cls._register_defaults()
        # -- Enterprise Phase 5c: air-gapped mode --
        if settings.air_gapped:
            return ["ollama"]
        return list(cls._providers.keys())

    @classmethod
    def _register_defaults(cls) -> None:
        cls.register("openai", OpenAIProvider())
        cls.register("anthropic", AnthropicProvider())
        cls.register("ollama", OllamaProvider())
