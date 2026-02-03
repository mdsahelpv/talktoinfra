"""
Agent service tools package.
"""

from app.tools.definitions import (
    ToolDefinition,
    ToolParameter,
    create_tool_definition,
    ToolRegistrySchema,
)
from app.tools.registry import ToolRegistry, get_registry, register_tool, tool
from app.tools.validators import (
    ValidationResult,
    PodQueryInput,
    LogQueryInput,
    DescribeResourceInput,
    validate_no_shell_injection,
    validate_k8s_resource_name,
    validate_namespace,
    validate_resource_type,
    sanitize_input,
    ALLOWED_NAMESPACES,
    DANGEROUS_PATTERNS,
)

__all__ = [
    # Definitions
    "ToolDefinition",
    "ToolParameter",
    "create_tool_definition",
    "ToolRegistrySchema",
    # Registry
    "ToolRegistry",
    "get_registry",
    "register_tool",
    "tool",
    # Validators
    "ValidationResult",
    "PodQueryInput",
    "LogQueryInput",
    "DescribeResourceInput",
    "validate_no_shell_injection",
    "validate_k8s_resource_name",
    "validate_namespace",
    "validate_resource_type",
    "sanitize_input",
    "ALLOWED_NAMESPACES",
    "DANGEROUS_PATTERNS",
]
