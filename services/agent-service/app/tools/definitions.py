"""
Tool definitions and schemas for the agent service.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, get_type_hints
from pydantic import BaseModel, create_model
import inspect


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    type: Type
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """Definition of a tool with metadata and schema."""

    name: str
    description: str
    parameters: List[ToolParameter]
    func: Callable
    read_only: bool = True
    category: str = "general"

    def get_schema(self) -> Dict[str, Any]:
        """Generate JSON schema for the tool."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": self._get_json_type(param.type),
                "description": param.description,
            }
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
            "read_only": self.read_only,
            "category": self.category,
        }

    def _get_json_type(self, python_type: Type) -> str:
        """Map Python types to JSON schema types."""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            List: "array",
            Dict: "object",
            Optional: "string",
        }
        return type_map.get(python_type, "string")

    def create_pydantic_model(self) -> Type[BaseModel]:
        """Create a Pydantic model for validation."""
        fields = {}
        for param in self.parameters:
            if param.required:
                fields[param.name] = (param.type, ...)
            else:
                fields[param.name] = (Optional[param.type], param.default)

        return create_model(
            f"{self.name.capitalize()}Input",
            **fields,
            __doc__=f"Input validation for {self.name}",
        )


class ToolRegistrySchema:
    """Schema for tool registry operations."""

    @staticmethod
    def get_registry_list_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Tool name"},
                "category": {"type": "string", "description": "Tool category"},
                "read_only": {
                    "type": "boolean",
                    "description": "Whether tool is read-only",
                },
            },
        }


def create_tool_definition(
    name: str,
    description: str,
    func: Callable,
    read_only: bool = True,
    category: str = "general",
) -> ToolDefinition:
    """
    Create a ToolDefinition from a function.
    Automatically extracts parameters from function signature.
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    parameters = []
    for param_name, param in sig.parameters.items():
        param_type = type_hints.get(param_name, str)
        description = (
            param.annotation.__doc__
            if hasattr(param.annotation, "__doc__")
            else f"Parameter {param_name}"
        )

        if param.default is inspect.Parameter.empty:
            required = True
            default = None
        else:
            required = False
            default = param.default

        parameters.append(
            ToolParameter(
                name=param_name,
                type=param_type,
                description=description,
                required=required,
                default=default,
            )
        )

    return ToolDefinition(
        name=name,
        description=description,
        parameters=parameters,
        func=func,
        read_only=read_only,
        category=category,
    )
