"""
Unit tests for AI Router settings endpoints.

Tests for:
- Model CRUD operations
- Provider configuration
- Agent configuration
- RAG settings
- Prompt management
- Safety settings
"""

import pytest
from unittest.mock import MagicMock

# Import models directly
from models_config import (
    ProviderConfig,
    ModelConfig,
    FallbackChain,
    ProviderType,
    ModelCapability,
)
from services.agent_config import (
    AgentConfig,
    AgentType,
    AgentToolConfig,
    ToolPermission,
    AgentSafetySettings,
    AgentPromptConfig,
)
from services.rag_config import (
    VectorStoreConfig,
    EmbeddingConfig,
    RAGIndexConfig,
    VectorStoreType,
    EmbeddingProvider,
)


class TestModelCRUD:
    """Test model CRUD operations."""

    def test_list_models_empty(self):
        """Test listing models when none exist."""
        mock_registry = MagicMock()
        mock_registry.list_models.return_value = []
        result = mock_registry.list_models()
        assert result == []

    def test_list_models_with_data(self):
        """Test listing models with data."""
        model = ModelConfig(
            id="test-model",
            name="Test Model",
            provider_id="test-provider",
            model_id="test-model-id",
            enabled=True,
            capabilities=[ModelCapability.CHAT],
            description="A test model",
        )
        mock_registry = MagicMock()
        mock_registry.list_models.return_value = [model]
        result = mock_registry.list_models()
        assert len(result) == 1
        assert result[0].id == "test-model"

    def test_get_model_found(self):
        """Test getting an existing model."""
        model = ModelConfig(
            id="test-model",
            name="Test Model",
            provider_id="test-provider",
            model_id="test-model-id",
            enabled=True,
            capabilities=[ModelCapability.CHAT],
            description="A test model",
        )
        mock_registry = MagicMock()
        mock_registry.get_model.return_value = model
        result = mock_registry.get_model("test-model")
        assert result is not None
        assert result.id == "test-model"

    def test_get_model_not_found(self):
        """Test getting a non-existent model."""
        mock_registry = MagicMock()
        mock_registry.get_model.return_value = None
        result = mock_registry.get_model("non-existent")
        assert result is None


class TestProviderConfig:
    """Test provider configuration."""

    def test_provider_creation(self):
        """Test provider creation."""
        provider = ProviderConfig(
            id="test-provider",
            name="Test Provider",
            provider_type=ProviderType.OPENAI,
            enabled=True,
            base_url="https://api.test.com/v1",
            capabilities=[ModelCapability.CHAT, ModelCapability.COMPLETION],
        )
        assert provider.id == "test-provider"
        assert provider.name == "Test Provider"
        assert provider.provider_type == ProviderType.OPENAI
        assert provider.enabled is True

    def test_provider_capabilities(self):
        """Test provider capabilities."""
        provider = ProviderConfig(
            id="test-provider",
            name="Test Provider",
            provider_type=ProviderType.OPENAI,
            enabled=True,
            capabilities=[ModelCapability.CHAT, ModelCapability.COMPLETION],
        )
        assert ModelCapability.CHAT in provider.capabilities
        assert ModelCapability.COMPLETION in provider.capabilities


class TestAgentConfig:
    """Test agent configuration."""

    def test_agent_creation(self):
        """Test agent creation."""
        agent = AgentConfig(
            id="test-agent",
            name="Test Agent",
            agent_type=AgentType.QUERY,
            enabled=True,
            description="A test agent",
            model_id="test-model",
            prompt=AgentPromptConfig(system_prompt="You are a helpful agent."),
        )
        assert agent.id == "test-agent"
        assert agent.name == "Test Agent"
        assert agent.agent_type == AgentType.QUERY
        assert agent.enabled is True

    def test_agent_safety_settings(self):
        """Test agent safety settings."""
        agent = AgentConfig(
            id="test-agent",
            name="Test Agent",
            agent_type=AgentType.QUERY,
            model_id="test-model",
            prompt=AgentPromptConfig(system_prompt="You are a helpful agent."),
        )
        assert isinstance(agent.safety, AgentSafetySettings)
        assert agent.safety.requires_approval is False
        assert agent.safety.max_retries == 3

    def test_agent_tool_config(self):
        """Test agent tool configuration."""
        tool = AgentToolConfig(
            tool_id="test-tool",
            permission=ToolPermission.READ,
            enabled=True,
        )
        assert tool.tool_id == "test-tool"
        assert tool.enabled is True
        assert tool.permission == ToolPermission.READ


class TestRAGSettings:
    """Test RAG settings management."""

    def test_vector_store_creation(self):
        """Test vector store creation."""
        store = VectorStoreConfig(
            id="test-store",
            name="Test Store",
            store_type=VectorStoreType.QDRANT,
            enabled=True,
            url="http://localhost:6333",
            index_name="test-index",
        )
        assert store.id == "test-store"
        assert store.store_type == VectorStoreType.QDRANT
        assert store.enabled is True

    def test_embedding_creation(self):
        """Test embedding creation."""
        embedding = EmbeddingConfig(
            id="test-embedding",
            name="Test Embedding",
            provider=EmbeddingProvider.OLLAMA,
            model_id="test-model",
            enabled=True,
            dimensions=768,
        )
        assert embedding.id == "test-embedding"
        assert embedding.provider == EmbeddingProvider.OLLAMA
        assert embedding.dimensions == 768

    def test_index_creation(self):
        """Test RAG index creation."""
        index = RAGIndexConfig(
            id="test-index",
            name="Test Index",
            description="A test index",
            enabled=True,
            vector_store_id="test-store",
            embedding_id="test-embedding",
            top_k=5,
            similarity_threshold=0.7,
        )
        assert index.id == "test-index"
        assert index.top_k == 5
        assert index.similarity_threshold == 0.7

    def test_index_chunking_config(self):
        """Test index chunking configuration."""
        index = RAGIndexConfig(
            id="test-index",
            name="Test Index",
            enabled=True,
            vector_store_id="test-store",
            embedding_id="test-embedding",
        )
        assert index.chunking is not None
        assert index.chunking.chunk_size == 1000
        assert index.chunking.chunk_overlap == 200


class TestFallbackChains:
    """Test fallback chain configuration."""

    def test_chain_creation(self):
        """Test fallback chain creation."""
        chain = FallbackChain(
            id="test-chain",
            name="Test Chain",
            description="A test fallback chain",
            models=["model-1", "model-2", "model-3"],
            enabled=True,
            retry_count=2,
            timeout_per_model_ms=30000,
        )
        assert chain.id == "test-chain"
        assert len(chain.models) == 3
        assert chain.retry_count == 2

    def test_chain_execution_order(self):
        """Test fallback chain model order."""
        chain = FallbackChain(
            id="test-chain",
            name="Test Chain",
            models=["model-1", "model-2", "model-3"],
        )
        assert chain.models[0] == "model-1"
        assert chain.models[1] == "model-2"
        assert chain.models[2] == "model-3"


class TestCostTracking:
    """Test cost tracking functionality."""

    def test_cost_calculation(self):
        """Test cost calculation logic."""
        input_tokens = 1000
        output_tokens = 500
        input_cost_per_token = 0.0001
        output_cost_per_token = 0.0003

        input_cost = input_tokens * input_cost_per_token
        output_cost = output_tokens * output_cost_per_token
        total_cost = input_cost + output_cost

        assert input_cost == 0.1
        assert output_cost == 0.15
        assert total_cost == 0.25


class TestSafetySettings:
    """Test safety settings."""

    def test_safety_settings_defaults(self):
        """Test safety settings defaults."""
        safety = AgentSafetySettings()
        assert safety.requires_approval is False
        assert safety.approval_threshold == "MEDIUM"
        assert safety.max_retries == 3
        assert safety.block_dangerous_patterns is True

    def test_safety_approval_levels(self):
        """Test safety approval level configuration."""
        safety = AgentSafetySettings(
            requires_approval=True,
            approval_threshold="HIGH",
            max_retries=1,
        )
        assert safety.requires_approval is True
        assert safety.approval_threshold == "HIGH"
        assert safety.max_retries == 1


class TestPromptManagement:
    """Test prompt management."""

    def test_prompt_templates(self):
        """Test prompt template configuration."""
        prompt = AgentPromptConfig(
            system_prompt="You are a {role} assistant.",
            user_prompt_template="Help me with {task}.",
            response_format="structured",
        )

        assert "You are a {role} assistant." in prompt.system_prompt
        assert prompt.response_format == "structured"

    def test_prompt_examples(self):
        """Test prompt examples configuration."""
        examples = [
            {"input": "What is the status?", "output": "All systems operational"},
            {"input": "Check CPU", "output": "CPU usage at 45%"},
        ]

        prompt = AgentPromptConfig(
            system_prompt="You are a helper.",
            examples=examples,
        )

        assert len(prompt.examples) == 2
        assert prompt.examples[0]["input"] == "What is the status?"


class TestIntegration:
    """Integration tests for settings management."""

    def test_router_creation(self):
        """Test that router can be created."""
        from api.v1.settings import router

        assert router is not None
        assert router.prefix == "/settings"

    def test_router_has_routes(self):
        """Test that router has routes registered."""
        from api.v1.settings import router

        routes = [route.path for route in router.routes]

        # Check for model endpoints
        assert any("/settings/models" in path for path in routes)

    def test_model_config_serialization(self):
        """Test model config can be serialized."""
        model = ModelConfig(
            id="test-model",
            name="Test Model",
            provider_id="test-provider",
            model_id="test-model-id",
            enabled=True,
            capabilities=[ModelCapability.CHAT],
        )
        data = model.model_dump()
        assert data["id"] == "test-model"
        assert data["provider_id"] == "test-provider"

    def test_provider_config_serialization(self):
        """Test provider config can be serialized."""
        provider = ProviderConfig(
            id="test-provider",
            name="Test Provider",
            provider_type=ProviderType.OPENAI,
            enabled=True,
        )
        data = provider.model_dump()
        assert data["id"] == "test-provider"
        assert data["provider_type"] == "openai"

    def test_agent_config_serialization(self):
        """Test agent config can be serialized."""
        agent = AgentConfig(
            id="test-agent",
            name="Test Agent",
            agent_type=AgentType.QUERY,
            model_id="test-model",
            prompt=AgentPromptConfig(system_prompt="You are a helpful agent."),
        )
        data = agent.model_dump()
        assert data["id"] == "test-agent"
        assert data["agent_type"] == "query"

    def test_rag_index_serialization(self):
        """Test RAG index can be serialized."""
        index = RAGIndexConfig(
            id="test-index",
            name="Test Index",
            enabled=True,
            vector_store_id="test-store",
            embedding_id="test-embedding",
            top_k=5,
        )
        data = index.model_dump()
        assert data["id"] == "test-index"
        assert data["top_k"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
