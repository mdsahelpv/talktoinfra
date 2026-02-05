"""
Settings API endpoints for AI Router.

Model management (providers, models, configurations)
Agent configuration (model assignment, prompts, tool access)
RAG configuration (vector store, embeddings, chunk settings)
Prompt management (templates, versioning)
Safety settings (approval thresholds, blocking rules)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

import structlog

from models_config import (
    ProviderConfig,
    ModelConfig,
    FallbackChain,
    CostTrackingEntry,
)
from services.model_manager import get_model_registry
from services.agent_config import (
    AgentConfig,
    AgentToolConfig,
    AgentSafetySettings,
    get_agent_config_service,
)
from services.rag_config import (
    VectorStoreConfig,
    EmbeddingConfig,
    RAGIndexConfig,
    get_rag_config_service,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/settings", tags=["settings"])

# Initialize services
model_registry = get_model_registry()
agent_config_service = get_agent_config_service()
rag_config_service = get_rag_config_service()


# ============== MODEL ENDPOINTS ==============


# Models
@router.get("/models", response_model=List[ModelConfig])
async def list_models(
    provider_id: Optional[str] = None,
    capabilities: Optional[List[str]] = Query(None),
    enabled_only: bool = Query(False),
):
    """List all models with optional filtering."""
    return model_registry.list_models(
        provider_id=provider_id,
        capabilities=capabilities,
    )


@router.get("/models/{model_id}", response_model=ModelConfig)
async def get_model(model_id: str):
    """Get a model by ID."""
    model = model_registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/models", response_model=ModelConfig, status_code=201)
async def create_model(model: ModelConfig):
    """Add a new model to the registry."""
    model_registry.add_model(model)
    return model


@router.put("/models/{model_id}", response_model=ModelConfig)
async def update_model(model_id: str, updates: Dict[str, Any]):
    """Update a model configuration."""
    model = model_registry.update_model(model_id, updates)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.delete("/models/{model_id}", status_code=204)
async def delete_model(model_id: str):
    """Delete a model from the registry."""
    if not model_registry.delete_model(model_id):
        raise HTTPException(status_code=404, detail="Model not found")


# Providers
@router.get("/providers", response_model=List[ProviderConfig])
async def list_providers(enabled_only: bool = Query(False)):
    """List all providers."""
    return model_registry.list_providers(enabled_only=enabled_only)


@router.get("/providers/{provider_id}", response_model=ProviderConfig)
async def get_provider(provider_id: str):
    """Get a provider by ID."""
    provider = model_registry.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.post("/providers", response_model=ProviderConfig, status_code=201)
async def create_provider(provider: ProviderConfig):
    """Add a new provider."""
    model_registry.add_provider(provider)
    return provider


@router.put("/providers/{provider_id}", response_model=ProviderConfig)
async def update_provider(provider_id: str, updates: Dict[str, Any]):
    """Update a provider configuration."""
    provider = model_registry.update_provider(provider_id, updates)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(provider_id: str):
    """Delete a provider from the registry."""
    if not model_registry.delete_provider(provider_id):
        raise HTTPException(status_code=404, detail="Provider not found")


# Fallback Chains
@router.get("/fallback-chains", response_model=List[FallbackChain])
async def list_fallback_chains():
    """List all fallback chains."""
    return model_registry.list_fallback_chains()


@router.get("/fallback-chains/{chain_id}", response_model=FallbackChain)
async def get_fallback_chain(chain_id: str):
    """Get a fallback chain by ID."""
    chain = model_registry.get_fallback_chain(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Fallback chain not found")
    return chain


@router.post("/fallback-chains", response_model=FallbackChain, status_code=201)
async def create_fallback_chain(chain: FallbackChain):
    """Add a new fallback chain."""
    model_registry.add_fallback_chain(chain)
    return chain


@router.put("/fallback-chains/{chain_id}", response_model=FallbackChain)
async def update_fallback_chain(chain_id: str, updates: Dict[str, Any]):
    """Update a fallback chain."""
    chain = model_registry.get_fallback_chain(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Fallback chain not found")

    for key, value in updates.items():
        if hasattr(chain, key) and key != "id":
            setattr(chain, key, value)

    return chain


# Cost Tracking
@router.get("/cost/summary")
async def get_cost_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Get cost summary for a time period."""
    return model_registry.get_cost_summary(start_date=start_date, end_date=end_date)


@router.get("/cost/usage")
async def get_usage_stats(model_id: Optional[str] = None):
    """Get model usage statistics."""
    return model_registry.get_usage_stats(model_id=model_id)


@router.post("/cost/track")
async def track_cost(entry: CostTrackingEntry):
    """Track cost for a single request."""
    model_registry.track_cost(entry)
    return {"status": "tracked"}


# ============== AGENT ENDPOINTS ==============


@router.get("/agents", response_model=List[AgentConfig])
async def list_agents(
    agent_type: Optional[str] = None,
    enabled_only: bool = Query(False),
):
    """List all agent configurations."""
    return agent_config_service.list_agents(
        agent_type=agent_type, enabled_only=enabled_only
    )


@router.get("/agents/{agent_id}", response_model=AgentConfig)
async def get_agent(agent_id: str):
    """Get an agent configuration by ID."""
    agent = agent_config_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/agents", response_model=AgentConfig, status_code=201)
async def create_agent(agent: AgentConfig):
    """Create a new agent configuration."""
    return agent_config_service.create_agent(agent)


@router.put("/agents/{agent_id}", response_model=AgentConfig)
async def update_agent(agent_id: str, updates: Dict[str, Any]):
    """Update an agent configuration."""
    agent = agent_config_service.update_agent(agent_id, updates)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str):
    """Delete an agent configuration."""
    if not agent_config_service.delete_agent(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")


# Agent Safety Settings
@router.get("/agents/{agent_id}/safety", response_model=AgentSafetySettings)
async def get_agent_safety(agent_id: str):
    """Get safety settings for an agent."""
    agent = agent_config_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.safety


@router.put("/agents/{agent_id}/safety", response_model=AgentConfig)
async def update_agent_safety(agent_id: str, updates: Dict[str, Any]):
    """Update safety settings for an agent."""
    agent = agent_config_service.update_agent_safety(agent_id, updates)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# Agent Tools
@router.get("/agents/{agent_id}/tools")
async def get_agent_tools(agent_id: str):
    """Get all tools for an agent."""
    tools = agent_config_service.get_agent_tools(agent_id)
    if agent_config_service.get_agent(agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return tools


@router.post("/agents/{agent_id}/tools", status_code=201)
async def add_agent_tool(agent_id: str, tool: AgentToolConfig):
    """Add a tool to an agent."""
    result = agent_config_service.add_tool_to_agent(agent_id, tool)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return result


@router.delete("/agents/{agent_id}/tools/{tool_id}", status_code=204)
async def remove_agent_tool(agent_id: str, tool_id: str):
    """Remove a tool from an agent."""
    result = agent_config_service.remove_tool_from_agent(agent_id, tool_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent not found")


# ============== RAG ENDPOINTS ==============


@router.get("/rag")
async def get_rag_settings():
    """Get global RAG settings."""
    return rag_config_service.get_settings()


@router.put("/rag")
async def update_rag_settings(updates: Dict[str, Any]):
    """Update global RAG settings."""
    return rag_config_service.update_settings(updates)


# Vector Stores
@router.get("/rag/vector-stores")
async def list_vector_stores(enabled_only: bool = Query(False)):
    """List all vector store configurations."""
    return rag_config_service.list_vector_stores(enabled_only=enabled_only)


@router.get("/rag/vector-stores/{store_id}", response_model=VectorStoreConfig)
async def get_vector_store(store_id: str):
    """Get a vector store by ID."""
    store = rag_config_service.get_vector_store(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Vector store not found")
    return store


@router.post("/rag/vector-stores", response_model=VectorStoreConfig, status_code=201)
async def create_vector_store(store: VectorStoreConfig):
    """Create a new vector store configuration."""
    return rag_config_service.create_vector_store(store)


@router.put("/rag/vector-stores/{store_id}", response_model=VectorStoreConfig)
async def update_vector_store(store_id: str, updates: Dict[str, Any]):
    """Update a vector store configuration."""
    store = rag_config_service.update_vector_store(store_id, updates)
    if not store:
        raise HTTPException(status_code=404, detail="Vector store not found")
    return store


@router.delete("/rag/vector-stores/{store_id}", status_code=204)
async def delete_vector_store(store_id: str):
    """Delete a vector store configuration."""
    if not rag_config_service.delete_vector_store(store_id):
        raise HTTPException(status_code=404, detail="Vector store not found")


# Embeddings
@router.get("/rag/embeddings")
async def list_embeddings(enabled_only: bool = Query(False)):
    """List all embedding configurations."""
    return rag_config_service.list_embeddings(enabled_only=enabled_only)


@router.get("/rag/embeddings/{embedding_id}", response_model=EmbeddingConfig)
async def get_embedding(embedding_id: str):
    """Get an embedding configuration by ID."""
    embedding = rag_config_service.get_embedding(embedding_id)
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")
    return embedding


@router.post("/rag/embeddings", response_model=EmbeddingConfig, status_code=201)
async def create_embedding(embedding: EmbeddingConfig):
    """Create a new embedding configuration."""
    return rag_config_service.create_embedding(embedding)


@router.put("/rag/embeddings/{embedding_id}", response_model=EmbeddingConfig)
async def update_embedding(embedding_id: str, updates: Dict[str, Any]):
    """Update an embedding configuration."""
    embedding = rag_config_service.update_embedding(embedding_id, updates)
    if not embedding:
        raise HTTPException(status_code=404, detail="Embedding not found")
    return embedding


@router.delete("/rag/embeddings/{embedding_id}", status_code=204)
async def delete_embedding(embedding_id: str):
    """Delete an embedding configuration."""
    if not rag_config_service.delete_embedding(embedding_id):
        raise HTTPException(status_code=404, detail="Embedding not found")


# Indexes
@router.get("/rag/indexes")
async def list_indexes(enabled_only: bool = Query(False)):
    """List all RAG index configurations."""
    return rag_config_service.list_indexes(enabled_only=enabled_only)


@router.get("/rag/indexes/{index_id}", response_model=RAGIndexConfig)
async def get_index(index_id: str):
    """Get an index configuration by ID."""
    index = rag_config_service.get_index(index_id)
    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    return index


@router.post("/rag/indexes", response_model=RAGIndexConfig, status_code=201)
async def create_index(index: RAGIndexConfig):
    """Create a new RAG index configuration."""
    return rag_config_service.create_index(index)


@router.put("/rag/indexes/{index_id}", response_model=RAGIndexConfig)
async def update_index(index_id: str, updates: Dict[str, Any]):
    """Update an index configuration."""
    index = rag_config_service.update_index(index_id, updates)
    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    return index


@router.delete("/rag/indexes/{index_id}", status_code=204)
async def delete_index(index_id: str):
    """Delete an index configuration."""
    if not rag_config_service.delete_index(index_id):
        raise HTTPException(status_code=404, detail="Index not found")


@router.post("/rag/indexes/{index_id}/rebuild")
async def rebuild_index(index_id: str):
    """Trigger index rebuild."""
    if not rag_config_service.rebuild_index(index_id):
        raise HTTPException(status_code=404, detail="Index not found")
    return {"status": "rebuild_started"}


@router.get("/rag/indexes/{index_id}/validate")
async def validate_index(index_id: str):
    """Validate index configuration."""
    return rag_config_service.validate_index_config(index_id)


@router.get("/rag/statistics")
async def get_rag_statistics():
    """Get RAG configuration statistics."""
    return rag_config_service.get_statistics()


# ============== EXPORT/IMPORT ENDPOINTS ==============


@router.get("/export/models")
async def export_model_registry():
    """Export model registry configuration."""
    return model_registry.export_registry()


@router.get("/export/agents")
async def export_agent_config():
    """Export agent configuration."""
    return agent_config_service.export_config()


@router.get("/export/rag")
async def export_rag_config():
    """Export RAG configuration."""
    return rag_config_service.export_config()


@router.post("/import/models")
async def import_model_registry(data: Dict[str, Any]):
    """Import model registry configuration."""
    model_registry.import_registry(data)
    return {"status": "imported"}


@router.post("/import/agents")
async def import_agent_config(data: Dict[str, Any]):
    """Import agent configuration."""
    agent_config_service.import_config(data)
    return {"status": "imported"}


@router.post("/import/rag")
async def import_rag_config(data: Dict[str, Any]):
    """Import RAG configuration."""
    rag_config_service.import_config(data)
    return {"status": "imported"}
