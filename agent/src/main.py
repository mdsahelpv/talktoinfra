"""Infra Agent entry point — connects to orchestrator and executes tool calls."""

import asyncio
import sys

from src.config import AgentConfig
from src.connectors.registry import ConnectorRegistry
from src.catalog.registry import ActionCatalogRegistry
from src.client.orchestrator_client import OrchestratorClient


async def main():
    config = AgentConfig()
    print(f"[agent] Starting TalkToInfra Agent v{config.version}")
    print(f"[agent] Connecting to orchestrator at {config.orchestrator_url}")

    connectors = ConnectorRegistry()
    await connectors.initialize_all(config)

    action_registry = ActionCatalogRegistry(connectors)

    client = OrchestratorClient(
        url=config.orchestrator_url,
        agent_id=config.agent_id,
        api_key=config.api_key,
    )

    async def on_tool_call(tool_call: dict) -> dict:
        action_name = tool_call.get("action", "")
        params = tool_call.get("parameters", {})
        print(f"[agent] Executing: {action_name}({params})")
        return await action_registry.execute(action_name, params)

    client.on_tool_call = on_tool_call

    await client.connect()

    try:
        await client.heartbeat_loop(interval=30)
    except KeyboardInterrupt:
        print("\n[agent] Shutting down...")
        await client.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
