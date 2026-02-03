"""
Agent Registry for registering and discovering agents.
Provides factory pattern for agent creation.
"""

from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import structlog

from app.agents.query_agent import get_query_agent
from app.agents.analysis_agent import get_analysis_agent
from app.agents.planning_agent import get_planning_agent
from app.agents.action_agent import get_action_agent

logger = structlog.get_logger()


class AgentType(str, Enum):
    """Types of agents available in the system."""

    QUERY = "query"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    ACTION = "action"


class AgentMetadata:
    """Metadata about a registered agent."""

    def __init__(
        self,
        agent_type: AgentType,
        name: str,
        description: str,
        factory: Callable[..., Any],
        requires_approval: bool,
        supports_auto_execute: bool,
        read_only: bool,
        category: str = "general",
    ):
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.factory = factory
        self.requires_approval = requires_approval
        self.supports_auto_execute = supports_auto_execute
        self.read_only = read_only
        self.category = category

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "agent_type": self.agent_type.value,
            "name": self.name,
            "description": self.description,
            "requires_approval": self.requires_approval,
            "supports_auto_execute": self.supports_auto_execute,
            "read_only": self.read_only,
            "category": self.category,
        }


class AgentRegistry:
    """
    Registry for managing and discovering agents.

    Implements factory pattern for agent instantiation:
    - Register agents with metadata
    - Discover agents by type or capabilities
    - Get agent instances
    - Query agent capabilities

    Example:
        registry = AgentRegistry()
        registry.register_default_agents()

        # Get agent by type
        query_agent = registry.get_agent(AgentType.QUERY)

        # List all agents
        all_agents = registry.list_agents()

        # Find by capability
        read_only_agents = registry.get_agents_by_capability(read_only=True)
    """

    def __init__(self):
        self._agents: Dict[AgentType, AgentMetadata] = {}
        self._instances: Dict[AgentType, Any] = {}
        self.logger = logger.bind(component="agent_registry")

    def register(
        self,
        agent_type: AgentType,
        name: str,
        description: str,
        factory: Callable[..., Any],
        requires_approval: bool = False,
        supports_auto_execute: bool = True,
        read_only: bool = True,
        category: str = "general",
    ) -> AgentMetadata:
        """
        Register an agent type.

        Args:
            agent_type: Type enum for the agent
            name: Human-readable name
            description: Description of agent capabilities
            factory: Factory function to create agent instances
            requires_approval: Whether actions require approval
            supports_auto_execute: Whether agent can auto-execute
            read_only: Whether agent only performs read operations
            category: Category for grouping

        Returns:
            AgentMetadata for the registered agent

        Raises:
            ValueError: If agent type already registered
        """
        if agent_type in self._agents:
            raise ValueError(f"Agent type '{agent_type.value}' is already registered")

        metadata = AgentMetadata(
            agent_type=agent_type,
            name=name,
            description=description,
            factory=factory,
            requires_approval=requires_approval,
            supports_auto_execute=supports_auto_execute,
            read_only=read_only,
            category=category,
        )

        self._agents[agent_type] = metadata

        self.logger.info(
            "agent_registered",
            agent_type=agent_type.value,
            name=name,
            read_only=read_only,
            requires_approval=requires_approval,
        )

        return metadata

    def get_agent(
        self,
        agent_type: AgentType,
        singleton: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        Get an agent instance.

        Args:
            agent_type: Type of agent to get
            singleton: If True, return cached instance; if False, create new
            **kwargs: Additional arguments for agent factory

        Returns:
            Agent instance

        Raises:
            ValueError: If agent type not registered
        """
        if agent_type not in self._agents:
            raise ValueError(f"Agent type '{agent_type.value}' not registered")

        # Return cached instance if singleton requested
        if singleton and agent_type in self._instances:
            return self._instances[agent_type]

        # Create new instance
        metadata = self._agents[agent_type]
        instance = metadata.factory(**kwargs)

        # Cache if singleton
        if singleton:
            self._instances[agent_type] = instance

        self.logger.debug(
            "agent_instance_created",
            agent_type=agent_type.value,
            singleton=singleton,
        )

        return instance

    def get_agent_by_type_str(self, agent_type_str: str, **kwargs: Any) -> Any:
        """
        Get agent by string type.

        Args:
            agent_type_str: String representation of agent type
            **kwargs: Additional arguments for agent factory

        Returns:
            Agent instance

        Raises:
            ValueError: If agent type string invalid
        """
        try:
            agent_type = AgentType(agent_type_str.lower())
        except ValueError:
            raise ValueError(
                f"Invalid agent type: '{agent_type_str}'. Valid types: {[t.value for t in AgentType]}"
            )

        return self.get_agent(agent_type, **kwargs)

    def list_agents(self) -> List[AgentMetadata]:
        """
        List all registered agents.

        Returns:
            List of AgentMetadata
        """
        return list(self._agents.values())

    def list_agent_types(self) -> List[str]:
        """
        List all registered agent type strings.

        Returns:
            List of agent type strings
        """
        return [t.value for t in self._agents.keys()]

    def get_agent_metadata(self, agent_type: AgentType) -> AgentMetadata:
        """
        Get metadata for an agent type.

        Args:
            agent_type: Type of agent

        Returns:
            AgentMetadata

        Raises:
            ValueError: If agent type not registered
        """
        if agent_type not in self._agents:
            raise ValueError(f"Agent type '{agent_type.value}' not registered")

        return self._agents[agent_type]

    def get_agents_by_capability(
        self,
        read_only: Optional[bool] = None,
        supports_auto_execute: Optional[bool] = None,
        requires_approval: Optional[bool] = None,
        category: Optional[str] = None,
    ) -> List[AgentMetadata]:
        """
        Find agents by capability filters.

        Args:
            read_only: Filter by read-only status
            supports_auto_execute: Filter by auto-execute capability
            requires_approval: Filter by approval requirement
            category: Filter by category

        Returns:
            List of matching AgentMetadata
        """
        results = []

        for metadata in self._agents.values():
            if read_only is not None and metadata.read_only != read_only:
                continue
            if (
                supports_auto_execute is not None
                and metadata.supports_auto_execute != supports_auto_execute
            ):
                continue
            if (
                requires_approval is not None
                and metadata.requires_approval != requires_approval
            ):
                continue
            if category is not None and metadata.category != category:
                continue

            results.append(metadata)

        return results

    def get_read_only_agents(self) -> List[AgentMetadata]:
        """Get all read-only agents (safe for auto-execution)."""
        return self.get_agents_by_capability(read_only=True)

    def get_modifying_agents(self) -> List[AgentMetadata]:
        """Get all agents that modify infrastructure."""
        return self.get_agents_by_capability(read_only=False)

    def is_registered(self, agent_type: AgentType) -> bool:
        """Check if an agent type is registered."""
        return agent_type in self._agents

    def register_default_agents(self) -> None:
        """
        Register all default agents.

        This registers the built-in agents:
        - Query Agent: Read-only queries
        - Analysis Agent: Insights and analysis (read-only)
        - Planning Agent: Plan generation (read-only)
        - Action Agent: Infrastructure modifications (requires approval)
        """
        # Register Query Agent
        self.register(
            agent_type=AgentType.QUERY,
            name="Query Agent",
            description="Read-only agent for infrastructure queries and information retrieval. Safe for auto-execution.",
            factory=get_query_agent,
            requires_approval=False,
            supports_auto_execute=True,
            read_only=True,
            category="query",
        )

        # Register Analysis Agent
        self.register(
            agent_type=AgentType.ANALYSIS,
            name="Analysis Agent",
            description="Read-only agent for insights, pattern detection, root cause analysis, and trend analysis. Safe for auto-execution.",
            factory=get_analysis_agent,
            requires_approval=False,
            supports_auto_execute=True,
            read_only=True,
            category="analysis",
        )

        # Register Planning Agent
        self.register(
            agent_type=AgentType.PLANNING,
            name="Planning Agent",
            description="Read-only agent for creating execution plans with risk assessment. Generates plans only - safe for auto-execution.",
            factory=get_planning_agent,
            requires_approval=False,
            supports_auto_execute=True,
            read_only=True,
            category="planning",
        )

        # Register Action Agent
        self.register(
            agent_type=AgentType.ACTION,
            name="Action Agent",
            description="Infrastructure modification agent. ALWAYS requires dry-run + approval. NEVER auto-executes.",
            factory=get_action_agent,
            requires_approval=True,
            supports_auto_execute=False,
            read_only=False,
            category="action",
        )

        self.logger.info("default_agents_registered", count=len(self._agents))

    def unregister(self, agent_type: AgentType) -> bool:
        """
        Unregister an agent type.

        Args:
            agent_type: Type to unregister

        Returns:
            True if unregistered, False if not found
        """
        if agent_type not in self._agents:
            return False

        del self._agents[agent_type]
        self._instances.pop(agent_type, None)

        self.logger.info("agent_unregistered", agent_type=agent_type.value)

        return True

    def clear(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
        self._instances.clear()

        self.logger.info("registry_cleared")

    def get_capabilities_summary(self) -> Dict[str, Any]:
        """
        Get summary of all registered agent capabilities.

        Returns:
            Dictionary with capability summary
        """
        summary = {
            "total_agents": len(self._agents),
            "agent_types": self.list_agent_types(),
            "read_only_agents": [
                m.agent_type.value for m in self.get_read_only_agents()
            ],
            "modifying_agents": [
                m.agent_type.value for m in self.get_modifying_agents()
            ],
            "agents_requiring_approval": [
                m.agent_type.value
                for m in self.get_agents_by_capability(requires_approval=True)
            ],
            "agents": {t.value: m.to_dict() for t, m in self._agents.items()},
        }

        return summary


# Global registry instance
_global_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """
    Get the global agent registry.

    Returns:
        AgentRegistry instance (creates with default agents if needed)
    """
    global _global_registry

    if _global_registry is None:
        _global_registry = AgentRegistry()
        _global_registry.register_default_agents()

    return _global_registry


def reset_agent_registry() -> AgentRegistry:
    """
    Reset and recreate the global agent registry.

    Returns:
        New AgentRegistry instance
    """
    global _global_registry

    _global_registry = AgentRegistry()
    _global_registry.register_default_agents()

    return _global_registry


# Convenience functions for direct access


def get_agent(agent_type: str, **kwargs: Any) -> Any:
    """
    Convenience function to get agent by type string.

    Args:
        agent_type: Agent type string
        **kwargs: Additional arguments

    Returns:
        Agent instance
    """
    registry = get_agent_registry()
    return registry.get_agent_by_type_str(agent_type, **kwargs)


def list_available_agents() -> List[Dict[str, Any]]:
    """
    List all available agents with metadata.

    Returns:
        List of agent metadata dictionaries
    """
    registry = get_agent_registry()
    return [m.to_dict() for m in registry.list_agents()]
