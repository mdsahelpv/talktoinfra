"""Intent router — classifies user intent and routes to the right handler."""

from src.config import settings
from src.llm.registry import LLMRegistry
from shared.python.catalog import ActionCatalog
from shared.python.models.action import ActionDefinition, InfraCategory


class IntentRouter:
    def __init__(self, catalog: ActionCatalog):
        self.catalog = catalog
        self.llm = LLMRegistry.get_provider(settings.default_llm_provider)

    async def route(self, action: ActionDefinition, parameters: dict) -> dict:
        """Execute a tool action by dispatching to the agent connector."""
        category_handlers = {
            InfraCategory.KUBERNETES: self._handle_k8s,
            InfraCategory.CLOUD: self._handle_cloud,
            InfraCategory.NETWORK: self._handle_network,
            InfraCategory.AD: self._handle_ad,
            InfraCategory.ONPREM: self._handle_onprem,
            InfraCategory.MONITORING: self._handle_monitoring,
            InfraCategory.DATABASE: self._handle_database,
        }
        handler = category_handlers.get(action.category)
        if not handler:
            return {"success": False, "error": f"No handler for category: {action.category}"}
        return await handler(action, parameters)

    async def _handle_k8s(self, action: ActionDefinition, params: dict) -> dict:
        from src.core.executors.k8s import execute_k8s_action
        return await execute_k8s_action(action.name, params)

    async def _handle_cloud(self, action: ActionDefinition, params: dict) -> dict:
        from src.core.executors.cloud import execute_cloud_action
        return await execute_cloud_action(action.name, params)

    async def _handle_network(self, action: ActionDefinition, params: dict) -> dict:
        from src.core.executors.network import execute_network_action
        return await execute_network_action(action.name, params)

    async def _handle_ad(self, action: ActionDefinition, params: dict) -> dict:
        from src.core.executors.ad import execute_ad_action
        return await execute_ad_action(action.name, params)

    async def _handle_onprem(self, action: ActionDefinition, params: dict) -> dict:
        from src.core.executors.onprem import execute_onprem_action
        return await execute_onprem_action(action.name, params)

    async def _handle_monitoring(self, action: ActionDefinition, params: dict) -> dict:
        from src.core.executors.monitoring import execute_monitoring_action
        return await execute_monitoring_action(action.name, params)

    async def _handle_database(self, action: ActionDefinition, params: dict) -> dict:
        return {"success": False, "error": "Database actions require the in-cluster agent"}
