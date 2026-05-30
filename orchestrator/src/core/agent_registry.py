"""Registry for sub-agents (K8s, Cloud, Network, AD, etc.)."""


class BaseAgent:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def get_status(self) -> str:
        return "available"

    def list_tools(self) -> list[str]:
        return []


class K8sAgent(BaseAgent):
    def __init__(self):
        super().__init__("k8s", "Kubernetes cluster management and diagnostics")

    def list_tools(self) -> list[str]:
        return [
            "k8s_get_pods", "k8s_describe_pod", "k8s_logs", "k8s_events",
            "k8s_top_pod", "k8s_get_deployments", "k8s_restart_deployment",
            "k8s_scale_deployment", "k8s_delete_pod", "k8s_get_nodes",
        ]


class CloudAgent(BaseAgent):
    def __init__(self):
        super().__init__("cloud", "Cloud infrastructure (AWS, Azure, GCP)")

    def list_tools(self) -> list[str]:
        return [
            "aws_list_ec2", "aws_describe_vpc", "aws_start_instance", "aws_stop_instance",
        ]


class NetworkAgent(BaseAgent):
    def __init__(self):
        super().__init__("network", "DNS, networking, and connectivity")

    def list_tools(self) -> list[str]:
        return ["dns_lookup", "network_ping", "network_port_check", "network_traceroute"]


class ADAgent(BaseAgent):
    def __init__(self):
        super().__init__("ad", "Active Directory and LDAP")

    def list_tools(self) -> list[str]:
        return ["ad_search_user", "ad_user_status", "ad_unlock_account", "ad_list_computers"]


class OnPremAgent(BaseAgent):
    def __init__(self):
        super().__init__("onprem", "On-premise servers via SSH")

    def list_tools(self) -> list[str]:
        return [
            "ssh_systemctl_status", "ssh_journalctl", "ssh_disk_usage",
            "ssh_memory_usage", "ssh_restart_service",
        ]


class MonitoringAgent(BaseAgent):
    def __init__(self):
        super().__init__("monitoring", "Prometheus and monitoring")

    def list_tools(self) -> list[str]:
        return ["prometheus_query", "prometheus_get_alerts"]


class DatabaseAgent(BaseAgent):
    def __init__(self):
        super().__init__("database", "Database management")

    def list_tools(self) -> list[str]:
        return ["db_list_databases", "db_slow_queries"]


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._register_defaults()

    def _register_defaults(self):
        for agent in [
            K8sAgent(), CloudAgent(), NetworkAgent(), ADAgent(),
            OnPremAgent(), MonitoringAgent(), DatabaseAgent(),
        ]:
            self._agents[agent.name] = agent

    def list_agents(self) -> list[dict]:
        return [
            {"name": a.name, "description": a.description, "tools": a.list_tools()}
            for a in self._agents.values()
        ]

    def get_agent(self, name: str) -> BaseAgent | None:
        return self._agents.get(name)
