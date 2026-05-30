from pydantic_settings import BaseSettings


class AgentConfig(BaseSettings):
    version: str = "0.1.0"
    agent_id: str = ""
    orchestrator_url: str = "http://localhost:8000"
    api_key: str = ""
    heartbeat_interval: int = 30

    # Kubernetes
    kubeconfig_path: str = ""
    k8s_enabled: bool = True

    # AWS
    aws_enabled: bool = True
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # DNS
    dns_enabled: bool = True

    # AD
    ad_enabled: bool = False
    ad_server: str = ""
    ad_domain: str = ""
    ad_username: str = ""
    ad_password: str = ""

    # SSH
    ssh_enabled: bool = False
    ssh_key_path: str = ""

    model_config = {"env_prefix": "TALKTOINFRA_AGENT_", "env_file": ".env"}
