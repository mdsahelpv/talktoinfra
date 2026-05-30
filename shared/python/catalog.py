"""Built-in action catalog — all tools the agent can use."""

from shared.python.models.action import (
    ActionDefinition, ActionParam, ActionCatalog,
    PermissionTier, InfraCategory,
)


def build_default_catalog() -> ActionCatalog:
    catalog = ActionCatalog()

    # ── Kubernetes ──────────────────────────────────────────────────────
    catalog.register(ActionDefinition(
        name="k8s_get_pods",
        description="List pods in a namespace",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="namespace", type="string", required=False, default="default"),
            ActionParam(name="label_selector", type="string", required=False),
            ActionParam(name="all_namespaces", type="boolean", required=False, default=False),
        ],
    ))
    catalog.register(ActionDefinition(
        name="k8s_describe_pod",
        description="Get detailed info about a pod",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="pod_name", type="string", required=True),
            ActionParam(name="namespace", type="string", required=False, default="default"),
        ],
    ))
    catalog.register(ActionDefinition(
        name="k8s_logs",
        description="Get logs from a pod",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="pod_name", type="string", required=True),
            ActionParam(name="namespace", type="string", required=False, default="default"),
            ActionParam(name="container", type="string", required=False),
            ActionParam(name="tail_lines", type="integer", required=False, default=100),
            ActionParam(name="previous", type="boolean", required=False, default=False),
        ],
    ))
    catalog.register(ActionDefinition(
        name="k8s_events",
        description="Get Kubernetes events",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="namespace", type="string", required=False),
            ActionParam(name="all_namespaces", type="boolean", required=False, default=False),
        ],
    ))
    catalog.register(ActionDefinition(
        name="k8s_top_pod",
        description="Show resource usage for pods",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="namespace", type="string", required=False, default="default"),
        ],
    ))
    catalog.register(ActionDefinition(
        name="k8s_get_deployments",
        description="List deployments in a namespace",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="namespace", type="string", required=False, default="default"),
        ],
    ))
    catalog.register(ActionDefinition(
        name="k8s_restart_deployment",
        description="Rollout restart a deployment",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.MUTATE,
        parameters=[
            ActionParam(name="name", type="string", required=True),
            ActionParam(name="namespace", type="string", required=False, default="default"),
        ],
    ))
    catalog.register(ActionDefinition(
        name="k8s_scale_deployment",
        description="Scale a deployment to N replicas",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.MUTATE,
        parameters=[
            ActionParam(name="name", type="string", required=True),
            ActionParam(name="namespace", type="string", required=False, default="default"),
            ActionParam(name="replicas", type="integer", required=True),
        ],
    ))
    catalog.register(ActionDefinition(
        name="k8s_delete_pod",
        description="Delete a pod (it will be recreated by the controller)",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.MUTATE,
        parameters=[
            ActionParam(name="pod_name", type="string", required=True),
            ActionParam(name="namespace", type="string", required=False, default="default"),
        ],
    ))
    catalog.register(ActionDefinition(
        name="k8s_get_nodes",
        description="List cluster nodes and their status",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.READ,
    ))

    # ── Network / DNS ──────────────────────────────────────────────────
    catalog.register(ActionDefinition(
        name="dns_lookup",
        description="DNS lookup for a hostname (A, AAAA, CNAME, MX records)",
        category=InfraCategory.NETWORK,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="hostname", type="string", required=True),
            ActionParam(name="record_type", type="string", required=False, default="A",
                       enum=["A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA"]),
            ActionParam(name="dns_server", type="string", required=False),
        ],
    ))
    catalog.register(ActionDefinition(
        name="network_ping",
        description="Ping a host to check reachability",
        category=InfraCategory.NETWORK,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="host", type="string", required=True),
            ActionParam(name="count", type="integer", required=False, default=4),
        ],
    ))
    catalog.register(ActionDefinition(
        name="network_port_check",
        description="Check if a TCP port is open on a host",
        category=InfraCategory.NETWORK,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="host", type="string", required=True),
            ActionParam(name="port", type="integer", required=True),
            ActionParam(name="protocol", type="string", required=False, default="tcp",
                       enum=["tcp", "udp"]),
        ],
    ))
    catalog.register(ActionDefinition(
        name="network_traceroute",
        description="Trace network path to a host",
        category=InfraCategory.NETWORK,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="host", type="string", required=True),
            ActionParam(name="max_hops", type="integer", required=False, default=30),
        ],
    ))

    # ── Active Directory ───────────────────────────────────────────────
    catalog.register(ActionDefinition(
        name="ad_search_user",
        description="Search for a user in Active Directory",
        category=InfraCategory.AD,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="username", type="string", required=True),
            ActionParam(name="attributes", type="array", required=False),
        ],
    ))
    catalog.register(ActionDefinition(
        name="ad_user_status",
        description="Check AD user account status (locked, enabled, last login)",
        category=InfraCategory.AD,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="username", type="string", required=True),
        ],
    ))
    catalog.register(ActionDefinition(
        name="ad_unlock_account",
        description="Unlock a locked AD user account",
        category=InfraCategory.AD,
        tier=PermissionTier.MUTATE,
        parameters=[
            ActionParam(name="username", type="string", required=True),
        ],
    ))
    catalog.register(ActionDefinition(
        name="ad_list_computers",
        description="List computers joined to the domain",
        category=InfraCategory.AD,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="search_base", type="string", required=False),
        ],
    ))

    # ── Cloud (AWS) ─────────────────────────────────────────────────────
    catalog.register(ActionDefinition(
        name="aws_list_ec2",
        description="List EC2 instances",
        category=InfraCategory.CLOUD,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="region", type="string", required=False),
            ActionParam(name="state", type="string", required=False,
                       enum=["running", "stopped", "terminated"]),
        ],
    ))
    catalog.register(ActionDefinition(
        name="aws_describe_vpc",
        description="Describe VPCs and subnets",
        category=InfraCategory.CLOUD,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="region", type="string", required=False),
        ],
    ))
    catalog.register(ActionDefinition(
        name="aws_start_instance",
        description="Start an EC2 instance",
        category=InfraCategory.CLOUD,
        tier=PermissionTier.MUTATE,
        parameters=[
            ActionParam(name="instance_id", type="string", required=True),
            ActionParam(name="region", type="string", required=False),
        ],
    ))
    catalog.register(ActionDefinition(
        name="aws_stop_instance",
        description="Stop an EC2 instance",
        category=InfraCategory.CLOUD,
        tier=PermissionTier.MUTATE,
        parameters=[
            ActionParam(name="instance_id", type="string", required=True),
            ActionParam(name="region", type="string", required=False),
        ],
    ))

    # ── On-Prem (SSH) ──────────────────────────────────────────────────
    catalog.register(ActionDefinition(
        name="ssh_systemctl_status",
        description="Check systemd service status on a remote host",
        category=InfraCategory.ONPREM,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="host", type="string", required=True),
            ActionParam(name="service", type="string", required=True),
        ],
    ))
    catalog.register(ActionDefinition(
        name="ssh_journalctl",
        description="Get systemd journal logs from a remote host",
        category=InfraCategory.ONPREM,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="host", type="string", required=True),
            ActionParam(name="service", type="string", required=False),
            ActionParam(name="tail_lines", type="integer", required=False, default=50),
            ActionParam(name="since", type="string", required=False),
        ],
    ))
    catalog.register(ActionDefinition(
        name="ssh_disk_usage",
        description="Check disk usage on a remote host",
        category=InfraCategory.ONPREM,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="host", type="string", required=True),
            ActionParam(name="path", type="string", required=False, default="/"),
        ],
    ))
    catalog.register(ActionDefinition(
        name="ssh_memory_usage",
        description="Check memory usage on a remote host",
        category=InfraCategory.ONPREM,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="host", type="string", required=True),
        ],
    ))
    catalog.register(ActionDefinition(
        name="ssh_restart_service",
        description="Restart a systemd service on a remote host",
        category=InfraCategory.ONPREM,
        tier=PermissionTier.MUTATE,
        parameters=[
            ActionParam(name="host", type="string", required=True),
            ActionParam(name="service", type="string", required=True),
        ],
    ))

    # ── Monitoring ─────────────────────────────────────────────────────
    catalog.register(ActionDefinition(
        name="prometheus_query",
        description="Run a PromQL query",
        category=InfraCategory.MONITORING,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="query", type="string", required=True),
            ActionParam(name="time_range", type="string", required=False, default="5m"),
        ],
    ))
    catalog.register(ActionDefinition(
        name="prometheus_get_alerts",
        description="List active Prometheus alerts",
        category=InfraCategory.MONITORING,
        tier=PermissionTier.READ,
    ))

    # ── Database ────────────────────────────────────────────────────────
    catalog.register(ActionDefinition(
        name="db_list_databases",
        description="List databases on a database server",
        category=InfraCategory.DATABASE,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="host", type="string", required=True),
            ActionParam(name="port", type="integer", required=False, default=5432),
            ActionParam(name="db_type", type="string", required=False, default="postgres",
                       enum=["postgres", "mysql"]),
        ],
    ))
    catalog.register(ActionDefinition(
        name="db_slow_queries",
        description="Get slow queries from a database",
        category=InfraCategory.DATABASE,
        tier=PermissionTier.READ,
        parameters=[
            ActionParam(name="host", type="string", required=True),
            ActionParam(name="db_type", type="string", required=False, default="postgres"),
            ActionParam(name="limit", type="integer", required=False, default=10),
        ],
    ))

    # ── Destructive actions ──────────────────────────────────────────
    catalog.register(ActionDefinition(
        name="k8s_delete_pod",
        description="Delete a Kubernetes pod (DESTRUCTIVE — requires fresh approval)",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.DESTRUCTIVE,
        parameters=[
            ActionParam(name="namespace", type="string", required=True),
            ActionParam(name="pod_name", type="string", required=True),
        ],
    ))
    catalog.register(ActionDefinition(
        name="k8s_delete_namespace",
        description="Delete a Kubernetes namespace and all its resources (DESTRUCTIVE)",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.DESTRUCTIVE,
        parameters=[
            ActionParam(name="namespace", type="string", required=True),
        ],
    ))

    return catalog
