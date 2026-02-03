"""
Query Agent for infrastructure queries.
Read-only agent safe for auto-execution.
"""

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from app.tools.registry import ToolRegistry, get_registry
from app.tools.k8s.read_tools import list_pods, get_pod, get_logs, describe_resource


@dataclass
class QueryIntent:
    """Parsed intent from a natural language query."""

    action: str
    resource_type: Optional[str] = None
    resource_name: Optional[str] = None
    namespace: Optional[str] = None
    parameters: Dict[str, Any] = None
    confidence: float = 0.0

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class QueryAgent:
    """
    Read-only query agent for infrastructure queries.
    Safe for auto-execution as all operations are read-only.
    """

    # Intent patterns for common queries
    INTENT_PATTERNS = [
        # List resources
        (
            r"show\s+(?:me\s+)?(?:all\s+)?pods\s*(?:in\s+namespace\s+(\S+))?",
            "list_pods",
            {"namespace_group": 1},
        ),
        (
            r"list\s+(?:all\s+)?pods\s*(?:in\s+namespace\s+(\S+))?",
            "list_pods",
            {"namespace_group": 1},
        ),
        (
            r"get\s+(?:all\s+)?pods\s*(?:in\s+namespace\s+(\S+))?",
            "list_pods",
            {"namespace_group": 1},
        ),
        # Get specific pod
        (
            r"(?:show|get|describe)\s+(?:me\s+)?pod\s+(\S+)\s*(?:in\s+namespace\s+(\S+))?",
            "get_pod",
            {"name_group": 1, "namespace_group": 2},
        ),
        # Get logs
        (
            r"(?:get|show|fetch)\s+(?:the\s+)?logs?(?:\s+for)?\s+(\S+)\s*(?:in\s+namespace\s+(\S+))?",
            "get_logs",
            {"name_group": 1, "namespace_group": 2},
        ),
        (
            r"logs?\s+(?:for\s+)?(\S+)\s*(?:in\s+namespace\s+(\S+))?",
            "get_logs",
            {"name_group": 1, "namespace_group": 2},
        ),
        # Describe resource
        (
            r"(?:describe|info\s+(?:about|on)|details?\s+(?:for|about))\s+(\S+)\s+(\S+)\s*(?:in\s+namespace\s+(\S+))?",
            "describe_resource",
            {"type_group": 1, "name_group": 2, "namespace_group": 3},
        ),
        (
            r"(?:describe|info\s+(?:about|on)|details?\s+(?:for|about))\s+(?:the\s+)?(\S+)\s+(?:called|named)?\s*(\S+)\s*(?:in\s+namespace\s+(\S+))?",
            "describe_resource",
            {"type_group": 1, "name_group": 2, "namespace_group": 3},
        ),
    ]

    # Resource type aliases
    RESOURCE_ALIASES = {
        "pod": "pod",
        "pods": "pod",
        "container": "pod",
        "containers": "pod",
        "service": "service",
        "services": "service",
        "svc": "service",
        "deployment": "deployment",
        "deployments": "deployment",
        "deploy": "deployment",
        "configmap": "configmap",
        "configmaps": "configmap",
        "cm": "configmap",
        "secret": "secret",
        "secrets": "secret",
        "node": "node",
        "nodes": "node",
        "namespace": "namespace",
        "namespaces": "namespace",
        "ns": "namespace",
        "ingress": "ingress",
        "ingresses": "ingress",
        "volume": "persistentvolume",
        "pv": "persistentvolume",
        "pvc": "persistentvolumeclaim",
        "claim": "persistentvolumeclaim",
    }

    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        Initialize the Query Agent.

        Args:
            registry: Optional tool registry to use (defaults to global)
        """
        self.registry = registry or get_registry()
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register default K8s read tools if not already registered."""
        default_tools = [
            (
                "list_pods",
                "List all pods in a namespace",
                list_pods,
                True,
                "kubernetes",
            ),
            (
                "get_pod",
                "Get detailed information about a specific pod",
                get_pod,
                True,
                "kubernetes",
            ),
            ("get_logs", "Get logs from a pod", get_logs, True, "kubernetes"),
            (
                "describe_resource",
                "Describe any Kubernetes resource",
                describe_resource,
                True,
                "kubernetes",
            ),
        ]

        for name, desc, func, read_only, category in default_tools:
            if name not in self.registry:
                self.registry.register(
                    name=name,
                    description=desc,
                    func=func,
                    read_only=read_only,
                    category=category,
                )

    def parse_query(self, query: str) -> QueryIntent:
        """
        Parse a natural language query to determine intent.

        Uses pattern matching for common queries. For complex queries,
        an LLM could be integrated here.

        Args:
            query: Natural language query string

        Returns:
            QueryIntent with parsed action and parameters
        """
        query_lower = query.lower().strip()

        # Try pattern matching first
        for pattern, action, groups in self.INTENT_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                params = {}
                resource_name = None
                namespace = None
                resource_type = None

                if "name_group" in groups:
                    idx = groups["name_group"]
                    if idx <= len(match.groups()) and match.group(idx):
                        resource_name = match.group(idx)

                if "namespace_group" in groups:
                    idx = groups["namespace_group"]
                    if idx <= len(match.groups()) and match.group(idx):
                        namespace = match.group(idx)

                if "type_group" in groups:
                    idx = groups["type_group"]
                    if idx <= len(match.groups()) and match.group(idx):
                        resource_type_raw = match.group(idx).lower()
                        resource_type = self.RESOURCE_ALIASES.get(
                            resource_type_raw, resource_type_raw
                        )

                # For list_pods, namespace might be the first match
                if action == "list_pods" and not namespace:
                    if match.group(1):
                        namespace = match.group(1)

                # Build parameters
                if resource_name:
                    if action == "get_pod" or action == "get_logs":
                        params["pod_name"] = resource_name
                    elif action == "describe_resource":
                        params["resource_name"] = resource_name

                if namespace:
                    params["namespace"] = namespace

                if resource_type and action == "describe_resource":
                    params["resource_type"] = resource_type

                return QueryIntent(
                    action=action,
                    resource_type=resource_type,
                    resource_name=resource_name,
                    namespace=namespace or "default",
                    parameters=params,
                    confidence=0.9,
                )

        # Fallback: try to use LLM-based parsing
        return self._parse_with_llm(query)

    def _parse_with_llm(self, query: str) -> QueryIntent:
        """
        Parse query using LLM for complex queries.
        This is a placeholder for LLM integration.

        Args:
            query: Natural language query

        Returns:
            QueryIntent
        """
        # In production, this would call an LLM to parse the query
        # For now, return a low-confidence unknown intent
        return QueryIntent(action="unknown", confidence=0.0)

    async def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute a natural language query.

        Args:
            query: Natural language query string

        Returns:
            Dictionary with query results
        """
        intent = self.parse_query(query)

        if intent.confidence == 0.0:
            return {
                "success": False,
                "error": "Could not understand query. Please try rephrasing.",
                "parsed_intent": {
                    "action": intent.action,
                    "resource_type": intent.resource_type,
                    "resource_name": intent.resource_name,
                    "namespace": intent.namespace,
                },
            }

        # Get the tool
        tool = self.registry.get_tool(intent.action)
        if not tool:
            return {
                "success": False,
                "error": f"Unknown action: {intent.action}",
                "parsed_intent": {
                    "action": intent.action,
                    "resource_type": intent.resource_type,
                    "resource_name": intent.resource_name,
                    "namespace": intent.namespace,
                },
            }

        # Execute the tool
        try:
            result = await self.registry.execute_tool(
                intent.action, **intent.parameters
            )

            return {
                "success": True,
                "query": query,
                "action": intent.action,
                "parameters": intent.parameters,
                "result": result,
            }

        except Exception as e:
            return {
                "success": False,
                "query": query,
                "action": intent.action,
                "parameters": intent.parameters,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def get_help(self) -> str:
        """Get help text for supported queries."""
        return """
Supported Queries:

**List Resources:**
- "Show me pods"
- "List pods in namespace X"
- "Get all pods"

**Get Specific Resource:**
- "Show pod my-pod"
- "Get pod my-pod in namespace X"
- "Describe pod my-pod"

**Get Logs:**
- "Get logs for my-pod"
- "Show logs my-pod in namespace X"
- "Logs for my-pod"

**Describe Resources:**
- "Describe deployment my-deployment"
- "Info about service my-service in namespace X"
- "Details for configmap my-config"

Note: This agent only supports READ operations. All write operations are disabled.
"""

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available read-only tools."""
        tools = self.registry.get_read_only_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "parameters": [
                    {
                        "name": p.name,
                        "type": str(p.type),
                        "required": p.required,
                        "description": p.description,
                    }
                    for p in tool.parameters
                ],
            }
            for tool in tools
        ]


# Global agent instance
_query_agent: Optional[QueryAgent] = None


def get_query_agent(registry: Optional[ToolRegistry] = None) -> QueryAgent:
    """Get or create the global query agent instance."""
    global _query_agent
    if _query_agent is None:
        _query_agent = QueryAgent(registry)
    return _query_agent
