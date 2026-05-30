"""Action catalog registry — maps action names to connector + handler."""

from src.connectors.registry import ConnectorRegistry


class ActionCatalogRegistry:
    """Maps each action name to its owning connector."""

    _action_map: dict[str, str] = {
        # K8s
        "k8s_get_pods": "kubernetes",
        "k8s_describe_pod": "kubernetes",
        "k8s_logs": "kubernetes",
        "k8s_events": "kubernetes",
        "k8s_top_pod": "kubernetes",
        "k8s_get_deployments": "kubernetes",
        "k8s_restart_deployment": "kubernetes",
        "k8s_scale_deployment": "kubernetes",
        "k8s_delete_pod": "kubernetes",
        "k8s_get_nodes": "kubernetes",
        # AWS
        "aws_list_ec2": "aws",
        "aws_describe_vpc": "aws",
        "aws_start_instance": "aws",
        "aws_stop_instance": "aws",
        # DNS / Network
        "dns_lookup": "dns",
        "network_ping": "dns",
        "network_port_check": "dns",
        # AD
        "ad_search_user": "active_directory",
        "ad_user_status": "active_directory",
        "ad_unlock_account": "active_directory",
        "ad_list_computers": "active_directory",
        # SSH
        "ssh_systemctl_status": "ssh",
        "ssh_journalctl": "ssh",
        "ssh_disk_usage": "ssh",
        "ssh_memory_usage": "ssh",
        "ssh_restart_service": "ssh",
    }

    def __init__(self, connectors: ConnectorRegistry):
        self._connectors = connectors

    async def execute(self, action_name: str, params: dict) -> dict:
        connector_name = self._action_map.get(action_name)
        if not connector_name:
            return {"success": False, "error": f"Unknown action: {action_name}"}

        connector = self._connectors.get(connector_name)
        if not connector:
            return {"success": False, "error": f"Connector not available: {connector_name}"}

        return await connector.execute(action_name, params)

    @classmethod
    def list_all_actions(cls) -> list[dict]:
        return [
            {"name": name, "connector": conn}
            for name, conn in cls._action_map.items()
        ]

    def list_actions(self) -> list[dict]:
        return self.list_all_actions()
