"""
Query pipeline for processing user queries.
Routes queries to appropriate handlers based on intent.
"""

import time
from typing import Any, Dict, List, Optional

import structlog

from conversation_models import (
    ConversationState,
    ConversationWorkflow,
)
from intent_classifier import IntentClassification, IntentClassifier
from rag_engine import RAGEngine
from llm_client import OllamaClient

logger = structlog.get_logger()


class QueryPipeline:
    """Process queries through intent classification, RAG, and generation."""

    def __init__(
        self,
        intent_classifier: IntentClassifier,
        rag_engine: RAGEngine,
        llm_client: OllamaClient,
    ):
        """Initialize query pipeline.

        Args:
            intent_classifier: Intent classification service
            rag_engine: RAG retrieval service
            llm_client: LLM generation service
        """
        self.intent_classifier = intent_classifier
        self.rag_engine = rag_engine
        self.llm_client = llm_client

    async def process(
        self,
        query: str,
        conversation_id: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Process a user query through the pipeline.

        Args:
            query: User query text
            conversation_id: Conversation ID
            user_id: User identifier
            conversation_history: Previous messages in conversation

        Returns:
            Pipeline result with response, sources, and workflow state
        """
        start_time = time.time()

        # Step 1: Classify intent
        intent = self.intent_classifier.classify(query)
        logger.info(
            "intent_classified",
            intent=intent.intent,
            confidence=intent.confidence,
        )

        # Step 2: Route based on intent type
        if intent.intent == "QUERY":
            result = await self._handle_query(query, intent, conversation_history)
        elif intent.intent == "ACTION":
            result = await self._handle_action(query, intent, conversation_id, user_id)
        elif intent.intent == "DISCOVERY":
            result = await self._handle_discovery(query, intent)
        elif intent.intent == "ONBOARDING":
            result = await self._handle_onboarding(query, intent)
        elif intent.intent == "MANAGEMENT":
            result = await self._handle_management(query, intent)
        else:
            result = await self._handle_default(query, intent)

        # Build workflow state
        workflow = ConversationWorkflow(
            conversation_id=conversation_id,
            current_state=ConversationState.COMPLETED,
            intent_type=intent.intent,
            target_resources=[e.get("value") for e in intent.entities],
        )

        duration = time.time() - start_time

        return {
            "response": result["response"],
            "sources": result.get("sources", []),
            "intent": intent.intent,
            "confidence": intent.confidence,
            "workflow": workflow,
            "processing_time": duration,
        }

    async def _handle_query(
        self,
        query: str,
        intent: IntentClassification,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Handle information retrieval queries using RAG."""
        # Retrieve relevant documents
        rag_results = await self.rag_engine.retrieve(query, top_k=10)

        # Build context from history
        context = self._build_history_context(history) if history else ""

        # Generate response
        prompt = self._build_query_prompt(query, rag_results, context)
        response = await self.llm_client.generate(prompt)

        # Convert to sources
        sources = [
            {
                "type": "vector_search",
                "resource_id": doc.get("id"),
                "resource_type": doc.get("resource_type"),
                "confidence": doc.get("score", 0.0),
                "metadata": doc.get("payload", {}),
            }
            for doc in rag_results
        ]

        return {"response": response, "sources": sources}

    async def _handle_action(
        self,
        query: str,
        intent: IntentClassification,
        conversation_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Handle action requests - requires approval."""
        # Generate structured action analysis
        prompt = f"""Analyze this infrastructure action request and provide details:

Request: {query}
Entities: {intent.entities}
Action Type: {intent.action_type}

Provide a JSON response with:
{{
    "action_type": "...",
    "target_resources": [...],
    "parameters": {{...}},
    "description": "...",
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "impact_summary": "...",
    "rollback_plan": "..." or null
}}
"""
        analysis = await self.llm_client.generate(prompt, model_type="code")

        return {
            "response": self._format_action_response(query, analysis),
            "sources": [
                {"type": "intent_classification", "confidence": intent.confidence}
            ],
            "requires_approval": True,
            "analysis": analysis,
        }

    async def _handle_discovery(
        self,
        query: str,
        intent: IntentClassification,
    ) -> Dict[str, Any]:
        """Handle discovery/exploration requests."""
        prompt = f"""You are an infrastructure discovery assistant.

User wants to discover or explore: {query}

Provide guidance on what will be discovered and how to proceed.
If this is a network scan or exploration request, explain the process.
"""
        response = await self.llm_client.generate(prompt)

        return {
            "response": response,
            "sources": [],
            "discovery_trigger": True,
        }

    async def _handle_onboarding(
        self,
        query: str,
        intent: IntentClassification,
    ) -> Dict[str, Any]:
        """Handle infrastructure onboarding requests."""
        prompt = f"""You are an infrastructure onboarding assistant.

User wants to add new infrastructure: {query}

Provide guidance on the onboarding process and what information is needed.
Explain how to connect the new infrastructure.
"""
        response = await self.llm_client.generate(prompt)

        return {
            "response": response,
            "sources": [],
            "onboarding_trigger": True,
        }

    async def _handle_management(
        self,
        query: str,
        intent: IntentClassification,
    ) -> Dict[str, Any]:
        """Handle management/settings requests."""
        prompt = f"""You are an infrastructure management assistant.

User request: {query}

Provide helpful guidance for settings, users, or management tasks.
"""
        response = await self.llm_client.generate(prompt)

        return {"response": response, "sources": []}

    async def _handle_default(
        self,
        query: str,
        intent: IntentClassification,
    ) -> Dict[str, Any]:
        """Handle unrecognized intents."""
        prompt = f"""You are a helpful infrastructure operations assistant.

User query: {query}

The system couldn't clearly classify this request. Provide a helpful response asking for clarification or offering general assistance.
"""
        response = await self.llm_client.generate(prompt)

        return {"response": response, "sources": []}

    def _build_history_context(self, history: List[Dict[str, Any]]) -> str:
        """Build context string from conversation history."""
        if not history:
            return ""

        context_parts = []
        for msg in history[-10:]:  # Last 10 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            context_parts.append(f"[{role.upper()}]: {content[:200]}")

        return "\n".join(context_parts)

    def _build_query_prompt(
        self,
        query: str,
        rag_results: List[Dict[str, Any]],
        history_context: str,
    ) -> str:
        """Build prompt for query response generation."""
        context_docs = []
        for i, doc in enumerate(rag_results, 1):
            payload = doc.get("payload", {})
            context_docs.append(
                f"[{i}] {payload.get('name', 'Unknown')} "
                f"({payload.get('resource_type', 'unknown')}): "
                f"{payload.get('description', 'No description')}"
            )

        context_str = (
            "\n".join(context_docs) if context_docs else "No relevant context found."
        )

        prompt = f"""You are an infrastructure operations assistant. Answer the user's question based on the retrieved context.

## Retrieved Context
{context_str}

## Conversation History
{history_context}

## User Question
{query}

## Instructions
- Provide a clear, concise answer based on the context
- If referencing specific resources, mention them by name
- Include source citations for your information
- If the context doesn't contain the answer, say so
- Use tables for structured data when appropriate

## Answer:
"""
        return prompt

    def _format_action_response(self, query: str, analysis: str) -> str:
        """Format action request response."""
        return f"""I've analyzed your action request: "{query}"

{analysis}

---

**Next Steps:**
- Review the action details above
- If you want to proceed, I'll request approval from the appropriate team member
- You can also run a "dry run" to preview the changes without executing them

Would you like to proceed with this action?
"""


class IntentAwareRouter:
    """Router that routes queries based on intent classification."""

    ROUTE_MAPPING = {
        "QUERY": "rag_pipeline",
        "ACTION": "action_engine",
        "DISCOVERY": "discovery_service",
        "ONBOARDING": "onboarding_service",
        "MANAGEMENT": "management_api",
        "ANALYSIS": "analysis_pipeline",
        "HELP": "help_handler",
        "UNKNOWN": "fallback_handler",
    }

    def __init__(self, base_url: str = "http://localhost"):
        """Initialize router.

        Args:
            base_url: Base URL for service endpoints
        """
        self.base_url = base_url

    def get_route(self, intent: str) -> str:
        """Get service route for intent.

        Args:
            intent: Classified intent type

        Returns:
            Service endpoint route
        """
        route = self.ROUTE_MAPPING.get(intent, "fallback_handler")
        return f"{self.base_url}/{route}"

    def should_use_rag(self, intent: str, confidence: float) -> bool:
        """Determine if RAG should be used for this intent.

        Args:
            intent: Classified intent type
            confidence: Classification confidence

        Returns:
            True if RAG should be used
        """
        if intent == "QUERY" and confidence >= 0.5:
            return True
        if intent == "ANALYSIS" and confidence >= 0.6:
            return True
        return False

    def get_confidence_threshold(self, intent: str) -> float:
        """Get confidence threshold for answering.

        Args:
            intent: Classified intent type

        Returns:
            Minimum confidence threshold
        """
        thresholds = {
            "QUERY": 0.4,
            "ACTION": 0.6,
            "DISCOVERY": 0.5,
            "ONBOARDING": 0.5,
            "MANAGEMENT": 0.5,
            "ANALYSIS": 0.6,
            "HELP": 0.3,
            "UNKNOWN": 0.2,
        }
        return thresholds.get(intent, 0.5)
