"""
Tool registry for managing and discovering tools.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Set
from functools import wraps

from app.tools.definitions import ToolDefinition, ToolParameter, create_tool_definition


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._categories: Dict[str, Set[str]] = {}

    def register(
        self,
        name: str,
        description: str,
        func: Callable,
        read_only: bool = True,
        category: str = "general",
        parameters: Optional[List[ToolParameter]] = None,
    ) -> ToolDefinition:
        """
        Register a tool in the registry.

        Args:
            name: Unique tool name
            description: Human-readable description
            func: The function to execute
            read_only: Whether the tool is read-only
            category: Tool category for grouping
            parameters: Optional explicit parameter definitions

        Returns:
            The created ToolDefinition
        """
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")

        if parameters:
            tool_def = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                func=func,
                read_only=read_only,
                category=category,
            )
        else:
            tool_def = create_tool_definition(
                name=name,
                description=description,
                func=func,
                read_only=read_only,
                category=category,
            )

        self._tools[name] = tool_def

        # Add to category
        if category not in self._categories:
            self._categories[category] = set()
        self._categories[category].add(name)

        return tool_def

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name to unregister

        Returns:
            True if tool was removed, False if not found
        """
        if name not in self._tools:
            return False

        tool_def = self._tools.pop(name)
        self._categories[tool_def.category].discard(name)

        return True

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """
        Get a tool definition by name.

        Args:
            name: Tool name

        Returns:
            ToolDefinition or None if not found
        """
        return self._tools.get(name)

    def list_tools(
        self, category: Optional[str] = None, read_only: Optional[bool] = None
    ) -> List[ToolDefinition]:
        """
        List all tools, optionally filtered.

        Args:
            category: Filter by category
            read_only: Filter by read_only status

        Returns:
            List of matching ToolDefinitions
        """
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        if read_only is not None:
            tools = [t for t in tools if t.read_only == read_only]

        return tools

    def list_categories(self) -> List[str]:
        """List all available categories."""
        return list(self._categories.keys())

    def get_tools_by_category(self, category: str) -> List[ToolDefinition]:
        """
        Get all tools in a category.

        Args:
            category: Category name

        Returns:
            List of ToolDefinitions in the category
        """
        if category not in self._categories:
            return []

        return [self._tools[name] for name in self._categories[category]]

    def search_tools(self, query: str) -> List[ToolDefinition]:
        """
        Search tools by name or description.

        Args:
            query: Search query string

        Returns:
            List of matching ToolDefinitions
        """
        query_lower = query.lower()
        return [
            tool
            for tool in self._tools.values()
            if query_lower in tool.name.lower()
            or query_lower in tool.description.lower()
        ]

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get JSON schemas for all registered tools."""
        return [tool.get_schema() for tool in self._tools.values()]

    def get_read_only_tools(self) -> List[ToolDefinition]:
        """Get all read-only tools (safe for auto-execution)."""
        return [tool for tool in self._tools.values() if tool.read_only]

    def get_modifying_tools(self) -> List[ToolDefinition]:
        """Get all tools that can modify state."""
        return [tool for tool in self._tools.values() if not tool.read_only]

    async def execute_tool(self, name: str, **kwargs: Any) -> Any:
        """
        Execute a registered tool.

        Args:
            name: Tool name
            **kwargs: Arguments to pass to the tool

        Returns:
            Tool execution result
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        # Validate inputs using Pydantic model
        input_model = tool.create_pydantic_model()
        validated = input_model(**kwargs)

        # Execute the tool
        if asyncio.iscoroutinefunction(tool.func):
            return await tool.func(**validated.dict())
        else:
            return tool.func(**validated.dict())

    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        read_only: bool = True,
        category: str = "general",
    ) -> Callable:
        """
        Decorator to register a function as a tool.

        Args:
            name: Tool name (defaults to function name)
            description: Tool description (defaults to docstring)
            read_only: Whether the tool is read-only
            category: Tool category

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_description = description or (
                func.__doc__ or "No description provided"
            )

            self.register(
                name=tool_name,
                description=tool_description,
                func=func,
                read_only=read_only,
                category=category,
            )

            return func

        return decorator

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._categories.clear()

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)

    def __iter__(self):
        """Iterate over registered tools."""
        return iter(self._tools.values())


# Global registry instance
_global_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _global_registry


def register_tool(
    name: str,
    description: str,
    func: Callable,
    read_only: bool = True,
    category: str = "general",
) -> ToolDefinition:
    """Register a tool in the global registry."""
    return _global_registry.register(
        name=name,
        description=description,
        func=func,
        read_only=read_only,
        category=category,
    )


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    read_only: bool = True,
    category: str = "general",
) -> Callable:
    """Decorator to register a function as a tool in the global registry."""
    return _global_registry.tool(
        name=name, description=description, read_only=read_only, category=category
    )
