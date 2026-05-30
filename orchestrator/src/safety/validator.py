"""Tool call argument validation."""

from shared.python.models.action import ActionDefinition


def validate_arguments(action: ActionDefinition, params: dict) -> tuple[bool, str]:
    """Validate that parameters match the action definition."""
    for param in action.parameters:
        if param.required and param.name not in params:
            return False, f"Missing required parameter: {param.name}"
        if param.name in params:
            value = params[param.name]
            if param.type == "string" and not isinstance(value, str):
                return False, f"Parameter {param.name} should be string, got {type(value).__name__}"
            if param.type == "integer" and not isinstance(value, int):
                return False, f"Parameter {param.name} should be integer, got {type(value).__name__}"
            if param.enum_values and value not in param.enum_values:
                return False, f"Parameter {param.name} must be one of: {', '.join(param.enum_values)}"
    return True, ""
