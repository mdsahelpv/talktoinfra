"""Tests for LLM provider interfaces."""

import pytest

from src.llm.registry import LLMRegistry


@pytest.mark.asyncio
async def test_openai_fallback():
    """Test that OpenAI provider returns fallback when not configured."""
    from src.llm.openai_provider import OpenAIProvider
    provider = OpenAIProvider()
    result = await provider.chat_completion(
        system_prompt="Test",
        messages=[{"role": "user", "content": "hello"}],
    )
    assert "not configured" in result["content"].lower()


@pytest.mark.asyncio
async def test_anthropic_fallback():
    from src.llm.anthropic_provider import AnthropicProvider
    provider = AnthropicProvider()
    result = await provider.chat_completion(
        system_prompt="Test",
        messages=[{"role": "user", "content": "hello"}],
    )
    assert "not configured" in result["content"].lower()


@pytest.mark.asyncio
async def test_ollama_fallback():
    from src.llm.ollama_provider import OllamaProvider
    provider = OllamaProvider()
    result = await provider.chat_completion(
        system_prompt="Test",
        messages=[{"role": "user", "content": "hello"}],
    )
    assert result is not None


def test_provider_registry():
    providers = LLMRegistry.list_providers()
    assert "openai" in providers
    assert "anthropic" in providers
    assert "ollama" in providers
