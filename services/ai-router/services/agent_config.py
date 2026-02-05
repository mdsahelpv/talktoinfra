"""
Agent configuration service.

Agent types (Query, Action, Analysis, Planning)
Model assignment per agent
Agent-specific system prompts
Tool access control per agent
Safety settings per agent
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

import structlog


logger = structlog.get_logger()


class AgentType(str, Enum):
    """Agent type enumeration."""

    QUERY = "query"
    ACTION = "action"
    ANALYSIS = "analysis"
    PLANNING = "planning"


class AgentState(str, Enum):
    """Agent execution state."""

    IDLE = "idle"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolPermission(str, Enum):
    """Tool permission levels."""

    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class AgentToolConfig(BaseModel):
    """Tool configuration for an agent."""

    tool_id: str = Field(..., description="Tool identifier")
    permission: ToolPermission = Field(
        default=ToolPermission.NONE, description="Permission level"
    )
    enabled: bool = Field(default=True, description="Tool enabled for agent")
    max_calls: Optional[int] = Field(None, description="Max calls per request")
    timeout_seconds: Optional[int] = Field(None, description="Tool timeout")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )


class AgentSafetySettings(BaseModel):
    """Safety settings for an agent."""

    requires_approval: bool = Field(
        default=False, description="Requires human approval"
    )
    approval_threshold: str = Field(
        default="MEDIUM", description="Risk level requiring approval"
    )
    auto_retry_on_failure: bool = Field(
        default=True, description="Auto retry on failure"
    )
    max_retries: int = Field(default=3, description="Max retry attempts")
    timeout_seconds: int = Field(default=300, description="Execution timeout")
    max_input_tokens: int = Field(default=16000, description="Max input tokens")
    max_output_tokens: int = Field(default=4096, description="Max output tokens")
    block_dangerous_patterns: bool = Field(
        default=True, description="Block dangerous patterns"
    )
    allowed_patterns: List[str] = Field(
        default_factory=list, description="Allowed patterns"
    )
    blocked_patterns: List[str] = Field(
        default_factory=list, description="Blocked patterns"
    )


class AgentPromptConfig(BaseModel):
    """Prompt configuration for an agent."""

    system_prompt: str = Field(..., description="System prompt for the agent")
    user_prompt_template: Optional[str] = Field(
        None, description="User prompt template"
    )
    context_template: Optional[str] = Field(None, description="Context template")
    response_format: str = Field(default="text", description="Response format")
    examples: List[Dict[str, str]] = Field(
        default_factory=list, description="Example conversations"
    )


class AgentConfig(BaseModel):
    """Complete agent configuration."""

    id: str = Field(..., description="Agent unique identifier")
    name: str = Field(..., description="Agent display name")
    agent_type: AgentType = Field(..., description="Agent type")
    enabled: bool = Field(default=True, description="Agent enabled status")
    description: Optional[str] = Field(None, description="Agent description")

    # Model Assignment
    model_id: str = Field(default="llama3.3:70b", description="Default model for agent")
    model_capabilities: List[str] = Field(
        default_factory=list, description="Required model capabilities"
    )

    # Prompt Configuration
    prompt: AgentPromptConfig = Field(
        default_factory=AgentPromptConfig, description="Prompt config"
    )

    # Tool Access
    tools: Dict[str, AgentToolConfig] = Field(
        default_factory=dict, description="Tool configurations"
    )

    # Safety Settings
    safety: AgentSafetySettings = Field(
        default_factory=AgentSafetySettings, description="Safety settings"
    )

    # Version tracking
    version: str = Field(default="1.0.0", description="Configuration version")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Created timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Updated timestamp"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class AgentConfigService:
    """Service for managing agent configurations."""

    def __init__(self) -> None:
        """Initialize the agent configuration service."""
        self.agents: Dict[str, AgentConfig] = {}
        self._load_default_configs()
        logger.info("agent_config_service_initialized")

    def _load_default_configs(self) -> None:
        """Load default agent configurations."""

        # Query Agent
        query_agent = AgentConfig(
            id="query-agent",
            name="Query Agent",
            agent_type=AgentType.QUERY,
            enabled=True,
            description="Agent for handling infrastructure queries",
            model_id="llama3.3:70b",
            model_capabilities=["chat", "reasoning"],
            prompt=AgentPromptConfig(
                system_prompt="""You are an infrastructure operations assistant.
Your role is to help users understand and query their infrastructure.

Guidelines:
- Provide clear, accurate information about infrastructure resources
- Use specific examples and references when available
- Suggest optimizations when you identify inefficiencies
- Escalate complex issues to appropriate teams

Current infrastructure context:""",
                response_format="text",
            ),
            safety=AgentSafetySettings(
                requires_approval=False,
                approval_threshold="HIGH",
                auto_retry_on_failure=True,
                max_retries=3,
                timeout_seconds=120,
            ),
        )
        self.agents["query-agent"] = query_agent

        # Action Agent
        action_agent = AgentConfig(
            id="action-agent",
            name="Action Agent",
            agent_type=AgentType.ACTION,
            enabled=True,
            description="Agent for executing infrastructure actions",
            model_id="llama3.3:70b",
            model_capabilities=["chat", "code"],
            prompt=AgentPromptConfig(
                system_prompt="""You are an infrastructure automation agent.
Your role is to safely execute infrastructure operations.

Safety Guidelines:
- Always validate inputs before execution
- Explain what you're about to do before doing it
- Provide rollback plans for destructive operations
- Escalate high-risk actions for human approval

For any action that modifies infrastructure:
1. Describe the action
2. Show the dry-run result
3. Request explicit approval if risk is medium or higher""",
                response_format="structured",
            ),
            safety=AgentSafetySettings(
                requires_approval=True,
                approval_threshold="MEDIUM",
                auto_retry_on_failure=True,
                max_retries=3,
                timeout_seconds=300,
                block_dangerous_patterns=True,
                blocked_patterns=["delete *", "rm -rf", "format disk"],
            ),
        )
        self.agents["action-agent"] = action_agent

        # Analysis Agent
        analysis_agent = AgentConfig(
            id="analysis-agent",
            name="Analysis Agent",
            agent_type=AgentType.ANALYSIS,
            enabled=True,
            description="Agent for analyzing infrastructure patterns and issues",
            model_id="llama3.3:70b",
            model_capabilities=["chat", "reasoning"],
            prompt=AgentPromptConfig(
                system_prompt="""You are an infrastructure analyst.
Your role is to analyze infrastructure data and provide insights.

Analysis Framework:
1. Current State Assessment
2. Trend Analysis
3. Anomaly Detection
4. Recommendations
5. Risk Assessment

Provide data-driven insights with supporting evidence.""",
                response_format="structured",
            ),
            safety=AgentSafetySettings(
                requires_approval=False,
                approval_threshold="HIGH",
                auto_retry_on_failure=True,
                max_retries=2,
                timeout_seconds=180,
            ),
        )
        self.agents["analysis-agent"] = analysis_agent

        # Planning Agent
        planning_agent = AgentConfig(
            id="planning-agent",
            name="Planning Agent",
            agent_type=AgentType.PLANNING,
            enabled=True,
            description="Agent for planning infrastructure changes",
            model_id="llama3.3:70b",
            model_capabilities=["chat", "reasoning"],
            prompt=AgentPromptConfig(
                system_prompt="""You are an infrastructure planning assistant.
Your role is to help plan infrastructure changes and migrations.

Planning Process:
1. Requirements Gathering
2. Current State Analysis
3. Gap Analysis
4. Solution Design
5. Implementation Plan
6. Risk Mitigation
7. Rollback Strategy

Think step-by-step and consider all dependencies.""",
                response_format="structured",
            ),
            safety=AgentSafetySettings(
                requires_approval=True,
                approval_threshold="LOW",
                auto_retry_on_failure=True,
                max_retries=2,
                timeout_seconds=300,
            ),
        )
        self.agents["planning-agent"] = planning_agent

    # CRUD Operations
    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get an agent configuration by ID."""
        return self.agents.get(agent_id)

    def list_agents(
        self, agent_type: Optional[str] = None, enabled_only: bool = False
    ) -> List[AgentConfig]:
        """List agent configurations."""
        agents = list(self.agents.values())

        if agent_type:
            agents = [a for a in agents if a.agent_type.value == agent_type]

        if enabled_only:
            agents = [a for a in agents if a.enabled]

        return agents

    def create_agent(self, agent: AgentConfig) -> AgentConfig:
        """Create a new agent configuration."""
        agent.created_at = datetime.utcnow()
        agent.updated_at = datetime.utcnow()
        self.agents[agent.id] = agent
        logger.info("agent_created", agent_id=agent.id, name=agent.name)
        return agent

    def update_agent(
        self, agent_id: str, updates: Dict[str, Any]
    ) -> Optional[AgentConfig]:
        """Update an agent configuration."""
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        for key, value in updates.items():
            if hasattr(agent, key) and key not in ("id", "created_at"):
                setattr(agent, key, value)

        agent.updated_at = datetime.utcnow()
        logger.info("agent_updated", agent_id=agent_id)
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent configuration."""
        if agent_id not in self.agents:
            return False

        del self.agents[agent_id]
        logger.info("agent_deleted", agent_id=agent_id)
        return True

    # Tool Management
    def add_tool_to_agent(
        self, agent_id: str, tool_config: AgentToolConfig
    ) -> Optional[AgentConfig]:
        """Add a tool to an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        agent.tools[tool_config.tool_id] = tool_config
        agent.updated_at = datetime.utcnow()
        logger.info(
            "tool_added_to_agent", agent_id=agent_id, tool_id=tool_config.tool_id
        )
        return agent

    def remove_tool_from_agent(
        self, agent_id: str, tool_id: str
    ) -> Optional[AgentConfig]:
        """Remove a tool from an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        if tool_id in agent.tools:
            del agent.tools[tool_id]
            agent.updated_at = datetime.utcnow()
            logger.info("tool_removed_from_agent", agent_id=agent_id, tool_id=tool_id)

        return agent

    def get_agent_tools(self, agent_id: str) -> List[AgentToolConfig]:
        """Get all tools for an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return []
        return list(agent.tools.values())

    # Safety Settings
    def update_agent_safety(
        self, agent_id: str, safety_updates: Dict[str, Any]
    ) -> Optional[AgentConfig]:
        """Update safety settings for an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        for key, value in safety_updates.items():
            if hasattr(agent.safety, key):
                setattr(agent.safety, key, value)

        agent.updated_at = datetime.utcnow()
        logger.info("agent_safety_updated", agent_id=agent_id)
        return agent

    # Prompt Management
    def update_agent_prompt(
        self, agent_id: str, prompt_updates: Dict[str, Any]
    ) -> Optional[AgentConfig]:
        """Update prompt settings for an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        for key, value in prompt_updates.items():
            if hasattr(agent.prompt, key):
                setattr(agent.prompt, key, value)

        agent.updated_at = datetime.utcnow()
        logger.info("agent_prompt_updated", agent_id=agent_id)
        return agent

    # Export/Import
    def export_config(self) -> Dict[str, Any]:
        """Export all agent configurations."""
        return {
            "agents": {k: v.model_dump() for k, v in self.agents.items()},
            "exported_at": datetime.utcnow().isoformat(),
        }

    def import_config(self, data: Dict[str, Any]) -> None:
        """Import agent configurations."""
        self.agents = {}
        for agent_id, agent_data in data.get("agents", {}).items():
            self.agents[agent_id] = AgentConfig(**agent_data)
        logger.info("agent_config_imported", count=len(self.agents))


def get_agent_config_service() -> AgentConfigService:
    """Get the agent configuration service singleton."""
    return AgentConfigService()
