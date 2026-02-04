"""
AI Router Service

Core intelligence service that:
- Classifies user query intents
- Routes queries to appropriate handlers
- Integrates with Ollama LLM for responses
- Implements RAG (Retrieval-Augmented Generation)
- Manages conversation context
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import get_settings
from intent_classifier import IntentClassifier
from conversation_manager import ConversationManager
from rag_engine import RAGEngine
from llm_client import OllamaClient
from query_pipeline import QueryPipeline
from approval_workflow import ApprovalWorkflow, RiskAssessor
from models import (
    QueryRequest,
    QueryResponse,
    IntentClassification,
    ConversationCreateRequest,
    ApprovalActionRequest,
)

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
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

# Service components
intent_classifier: Optional[IntentClassifier] = None
conversation_manager: Optional[ConversationManager] = None
rag_engine: Optional[RAGEngine] = None
llm_client: Optional[OllamaClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global intent_classifier, conversation_manager, rag_engine, llm_client

    settings = get_settings()

    # Initialize components
    logger.info("ai_router_initializing")

    intent_classifier = IntentClassifier()
    conversation_manager = ConversationManager(
        redis_url=settings.redis_url, postgres_url=settings.postgres_url
    )
    rag_engine = RAGEngine(
        qdrant_url=settings.qdrant_url, ollama_host=settings.ollama_host
    )
    llm_client = OllamaClient(
        host=settings.ollama_host,
        model_chat=settings.ollama_model_chat,
        model_code=settings.ollama_model_code,
    )

    # Test connections
    try:
        await rag_engine.health_check()
        await llm_client.health_check()
        logger.info("ai_router_ready")
    except Exception as e:
        logger.error("ai_router_init_failed", error=str(e))
        raise

    yield

    # Cleanup
    logger.info("ai_router_shutting_down")


app = FastAPI(
    title="AI Infrastructure Operations - AI Router",
    description="Intent classification, LLM routing, and RAG",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests with context."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    with structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    ):
        logger.info("request_started")
        response = await call_next(request)
        logger.info("request_completed", status_code=response.status_code)
        return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health = {
        "status": "healthy",
        "service": "ai-router",
        "timestamp": time.time(),
        "components": {},
    }

    # Check RAG engine
    try:
        await rag_engine.health_check()
        health["components"]["rag_engine"] = "healthy"
    except Exception as e:
        health["components"]["rag_engine"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"

    # Check LLM client
    try:
        await llm_client.health_check()
        health["components"]["llm_client"] = "healthy"
    except Exception as e:
        health["components"]["llm_client"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"

    return health


@app.post("/query", response_model=QueryResponse)
async def process_query(
    request: Request,
    query: QueryRequest,
    background_tasks: BackgroundTasks,
):
    """Process a natural language query."""
    start_time = time.time()

    try:
        # 1. Get or create conversation
        conversation = await conversation_manager.get_or_create(
            query.conversation_id, query.user_id
        )

        # 2. Classify intent
        intent = intent_classifier.classify(query.query)
        logger.info(
            "intent_classified",
            intent=intent.intent,
            confidence=intent.confidence,
            entities=intent.entities,
        )

        # 3. Retrieve context based on intent
        context = await build_context(query, intent, conversation)

        # 4. Generate response based on intent type
        if intent.intent == "QUERY":
            response_text, sources = await handle_query_intent(query, context, intent)
        elif intent.intent == "ACTION":
            response_text, sources = await handle_action_intent(query, context, intent)
        elif intent.intent == "ANALYSIS":
            response_text, sources = await handle_analysis_intent(
                query, context, intent
            )
        else:
            response_text, sources = await handle_help_intent(query, context)

        # 5. Store in conversation history
        await conversation_manager.add_message(
            conversation_id=conversation.id,
            role="user",
            content=query.query,
        )
        await conversation_manager.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text,
            metadata={
                "intent": intent.intent,
                "sources": [s.model_dump() for s in sources],
            },
        )

        # 6. Log metrics
        duration = time.time() - start_time
        logger.info(
            "query_processed",
            duration=duration,
            intent=intent.intent,
            conversation_id=conversation.id,
        )

        return QueryResponse(
            response=response_text,
            conversation_id=conversation.id,
            sources=sources,
            metadata={
                "intent": intent.intent,
                "confidence": intent.confidence,
                "processing_time": duration,
                "model": llm_client.model_chat,
            },
        )

    except Exception as e:
        logger.error("query_processing_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to process query: {str(e)}"
        )


@app.post("/query/stream")
async def process_query_stream(request: Request, query: QueryRequest):
    """Process query with streaming response."""

    async def generate():
        try:
            # Classify intent
            intent = intent_classifier.classify(query.query)

            # Get RAG context
            rag_context = await rag_engine.retrieve(query.query, top_k=5)

            # Build prompt
            prompt = build_prompt(query.query, intent, rag_context)

            # Stream from LLM
            async for chunk in llm_client.generate_stream(prompt):
                yield chunk

        except Exception as e:
            logger.error("streaming_error", error=str(e))
            yield f"\n[Error: {str(e)}]"

    return StreamingResponse(
        generate(), media_type="text/plain", headers={"X-Accel-Buffering": "no"}
    )


async def build_context(
    query: QueryRequest, intent: IntentClassification, conversation: Any
) -> Dict[str, Any]:
    """Build context for query processing."""
    context = {
        "conversation_history": conversation.messages[-5:] if conversation else [],
        "user_context": query.context or {},
        "timestamp": time.time(),
    }

    # Add RAG-retrieved context for relevant intents
    if intent.intent in ["QUERY", "ANALYSIS"]:
        rag_results = await rag_engine.retrieve(query.query, top_k=5)
        context["retrieved_documents"] = rag_results

    return context


async def handle_query_intent(
    query: QueryRequest, context: Dict[str, Any], intent: IntentClassification
) -> tuple[str, List[Any]]:
    """Handle information retrieval queries."""

    # Build RAG prompt
    rag_docs = context.get("retrieved_documents", [])
    prompt = f"""You are an infrastructure operations assistant answering questions based on the provided context.

Context from infrastructure search:
{format_rag_context(rag_docs)}

User Question: {query.query}

Provide a clear, concise answer. If you reference specific resources, mention them by name.
If the context doesn't contain the answer, say so and suggest what information might be needed.
"""

    response = await llm_client.generate(prompt)

    # Convert RAG results to sources
    sources = [
        {
            "type": "vector_search",
            "resource_id": doc.get("id"),
            "resource_type": doc.get("resource_type"),
            "confidence": doc.get("score", 0.0),
            "metadata": doc.get("payload", {}),
        }
        for doc in rag_docs
    ]

    return response, sources


async def handle_action_intent(
    query: QueryRequest, context: Dict[str, Any], intent: IntentClassification
) -> tuple[str, List[Any]]:
    """Handle action execution requests."""

    prompt = f"""You are analyzing an infrastructure action request.

User Request: {query.query}
Extracted Entities: {intent.entities}

Determine:
1. What action is being requested (restart, scale, deploy, etc.)
2. What is the target resource
3. What parameters are involved
4. What risks might be involved

Respond in JSON format:
{{
    "action_type": "...",
    "target_resource": "...",
    "parameters": {{...}},
    "risks": [...],
    "requires_approval": true/false,
    "suggested_approvers": [...]
}}
"""

    response = await llm_client.generate(prompt, model_type="code")

    # Parse the structured response
    sources = [
        {
            "type": "intent_classification",
            "resource_type": "action_analysis",
            "confidence": intent.confidence,
            "metadata": {"entities": intent.entities},
        }
    ]

    # Add user-friendly message
    user_response = f"""I've analyzed your action request. 

Based on your request: "{query.query}"

The action requires dry-run validation before execution. Please use the action execution endpoint to proceed with dry-run mode enabled.

Analysis: {response}"""

    return user_response, sources


async def handle_analysis_intent(
    query: QueryRequest, context: Dict[str, Any], intent: IntentClassification
) -> tuple[str, List[Any]]:
    """Handle analysis and insight requests."""

    rag_docs = context.get("retrieved_documents", [])

    prompt = f"""You are an infrastructure analyst providing insights and analysis.

Context from infrastructure data:
{format_rag_context(rag_docs)}

Analysis Request: {query.query}

Provide:
1. A summary of the current state
2. Key insights or patterns you notice
3. Recommendations for optimization or improvement
4. Any potential issues or risks

Be data-driven and specific in your recommendations.
"""

    response = await llm_client.generate(prompt)

    sources = [
        {
            "type": "vector_search",
            "resource_id": doc.get("id"),
            "resource_type": doc.get("resource_type"),
            "confidence": doc.get("score", 0.0),
            "metadata": doc.get("payload", {}),
        }
        for doc in rag_docs
    ]

    return response, sources


async def handle_help_intent(
    query: QueryRequest, context: Dict[str, Any]
) -> tuple[str, List[Any]]:
    """Handle help and explanation requests."""

    prompt = f"""You are a helpful infrastructure operations assistant.

User is asking for help: {query.query}

Provide clear, helpful guidance. Include examples where appropriate.
Explain what you can help with:
- Querying infrastructure ("Show me pods in namespace X")
- Analyzing data ("What changed in the last hour?")
- Executing actions ("Restart service Y") - requires approval
- Getting recommendations
"""

    response = await llm_client.generate(prompt)

    return response, []


def format_rag_context(docs: List[Dict]) -> str:
    """Format RAG documents for prompt context."""
    if not docs:
        return "No relevant context found."

    context_parts = []
    for i, doc in enumerate(docs, 1):
        payload = doc.get("payload", {})
        context_parts.append(
            f"[{i}] {payload.get('name', 'Unknown')} "
            f"({payload.get('resource_type', 'unknown')}): "
            f"{payload.get('description', 'No description')}"
        )

    return "\n".join(context_parts)


def build_prompt(query: str, intent: IntentClassification, context: List[Dict]) -> str:
    """Build final prompt for LLM."""
    return f"""Query: {query}
Intent: {intent.intent}
Context: {format_rag_context(context)}

Response:"""


# Conversation endpoints
@app.post("/conversations")
async def create_conversation(request: ConversationCreateRequest):
    """Create a new conversation."""
    try:
        conversation = await conversation_manager.create_conversation(
            user_id=request.user_id,
            title=request.title,
            metadata=request.metadata,
        )
        return conversation
    except Exception as e:
        logger.error("create_conversation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a conversation by ID."""
    conversation = await conversation_manager.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.get("/conversations")
async def list_conversations(user_id: str, limit: int = 20, offset: int = 0):
    """List conversations for a user."""
    conversations = await conversation_manager.list_conversations(
        user_id=user_id, limit=limit, offset=offset
    )
    return {"items": conversations, "total": len(conversations)}


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    success = await conversation_manager.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted"}


@app.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    """Get messages for a conversation."""
    conversation = await conversation_manager.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation.get("messages", [])


# Approval endpoints
@app.post("/approvals")
async def create_approval(
    request: Request,
    data: dict,
):
    """Create an approval request for an action."""
    try:
        from conversation_models import RiskLevel, ActionApproval
        from approval_workflow import ApprovalWorkflow

        settings = get_settings()
        approval_workflow = ApprovalWorkflow(
            redis_url=settings.redis_url,
            postgres_url=settings.postgres_url,
        )

        approval = await approval_workflow.create_approval(
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
            action_type=data["action_type"],
            target_resources=data.get("target_resources", []),
            description=data["description"],
            risk_level=RiskLevel(data["risk_level"]),
            impact_summary=data["impact_summary"],
            rollback_plan=data.get("rollback_plan"),
            metadata=data.get("metadata"),
        )

        logger.info(
            "approval_created",
            approval_id=approval.id,
            conversation_id=approval.conversation_id,
        )

        return approval
    except Exception as e:
        logger.error("create_approval_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/approvals/{approval_id}")
async def get_approval(approval_id: str):
    """Get an approval request by ID."""
    from approval_workflow import ApprovalWorkflow
    from config import get_settings

    settings = get_settings()
    approval_workflow = ApprovalWorkflow(
        redis_url=settings.redis_url,
        postgres_url=settings.postgres_url,
    )

    approval = await approval_workflow.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.post("/approvals/{approval_id}/approve")
async def approve_action(approval_id: str, request: ApprovalActionRequest):
    """Approve an action."""
    from approval_workflow import ApprovalWorkflow
    from config import get_settings

    settings = get_settings()
    approval_workflow = ApprovalWorkflow(
        redis_url=settings.redis_url,
        postgres_url=settings.postgres_url,
    )

    approval = await approval_workflow.approve(
        approval_id=approval_id,
        approver_id=request.action,
        reason=request.reason,
    )

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    logger.info(
        "action_approved",
        approval_id=approval_id,
        approver_id=request.action,
    )

    return approval


@app.post("/approvals/{approval_id}/reject")
async def reject_action(approval_id: str, request: ApprovalActionRequest):
    """Reject an action."""
    from approval_workflow import ApprovalWorkflow
    from config import get_settings

    settings = get_settings()
    approval_workflow = ApprovalWorkflow(
        redis_url=settings.redis_url,
        postgres_url=settings.postgres_url,
    )

    if not request.reason:
        raise HTTPException(
            status_code=400, detail="Rejection reason is required")

    approval = await approval_workflow.reject(
        approval_id=approval_id,
        approver_id=request.action,
        reason=request.reason,
    )

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    logger.info(
        "action_rejected",
        approval_id=approval_id,
        reason=request.reason,
    )

    return approval


@app.get("/approvals/pending")
async def list_pending_approvals(limit: int = 50):
    """List all pending approvals."""
    from approval_workflow import ApprovalWorkflow
    from config import get_settings

    settings = get_settings()
    approval_workflow = ApprovalWorkflow(
        redis_url=settings.redis_url,
        postgres_url=settings.postgres_url,
    )

    approvals = await approval_workflow.list_pending(limit=limit)
    return approvals


@app.get("/conversations/{conversation_id}/approvals")
async def get_conversation_approvals(conversation_id: str):
    """Get all approvals for a conversation."""
    from approval_workflow import ApprovalWorkflow
    from config import get_settings

    settings = get_settings()
    approval_workflow = ApprovalWorkflow(
        redis_url=settings.redis_url,
        postgres_url=settings.postgres_url,
    )

    approvals = await approval_workflow.get_conversation_approvals(conversation_id)
    return approvals


# Intent classification endpoint
@app.post("/classify")
async def classify_intent(request: Request, data: dict):
    """Classify the intent of a query."""
    intent = intent_classifier.classify(data["query"])
    return {
        "intent": intent.intent,
        "confidence": intent.confidence,
        "entities": intent.entities,
        "action_type": intent.action_type,
        "target_resource": intent.target_resource,
        "requires_approval": intent.requires_approval,
        "risk_level": intent.risk_level,
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
