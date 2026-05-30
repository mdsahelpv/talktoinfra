"""Kubernetes connector using the official Python client."""

from kubernetes import config, client
from kubernetes.client import ApiException

from src.connectors.base import BaseConnector
from src.config import AgentConfig


class K8sConnector(BaseConnector):
    def __init__(self, cfg: AgentConfig):
        self._available = False
        self._cfg = cfg
        self._api = None
        self._core = None
        self._apps = None

    async def initialize(self) -> None:
        try:
            if self._cfg.kubeconfig_path:
                config.load_kube_config(config_file=self._cfg.kubeconfig_path)
            else:
                config.load_incluster_config()
            self._api = client.CoreV1Api()
            self._apps = client.AppsV1Api()
            self._available = True
        except Exception as e:
            print(f"[k8s] Init failed: {e}")
            self._available = False

    @property
    def name(self) -> str:
        return "kubernetes"

    @property
    def is_available(self) -> bool:
        return self._available

    async def health(self) -> dict:
        if not self._available:
            return {"healthy": False, "error": "Not initialized"}
        try:
            version = self._api.get_code()
            return {"healthy": True, "version": version.git_version}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    async def execute(self, action: str, params: dict) -> dict:
        if not self._available:
            return {"success": False, "error": "K8s connector not available"}
        try:
            handler = self._get_handler(action)
            if not handler:
                return {"success": False, "error": f"Unknown K8s action: {action}"}
            return await handler(params)
        except ApiException as e:
            return {"success": False, "error": f"K8s API error: {e.reason} ({e.status})"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_handler(self, action: str):
        handlers = {
            "k8s_get_pods": self._get_pods,
            "k8s_describe_pod": self._describe_pod,
            "k8s_logs": self._get_logs,
            "k8s_events": self._get_events,
            "k8s_get_deployments": self._get_deployments,
            "k8s_restart_deployment": self._restart_deployment,
            "k8s_scale_deployment": self._scale_deployment,
            "k8s_delete_pod": self._delete_pod,
            "k8s_get_nodes": self._get_nodes,
            "k8s_top_pod": self._top_pod,
        }
        return handlers.get(action)

    async def _get_pods(self, params: dict) -> dict:
        ns = params.get("namespace", "default")
        if params.get("all_namespaces", False):
            pods = self._api.list_pod_for_all_namespaces()
        else:
            pods = self._api.list_namespaced_pod(ns)
        items = []
        for p in pods.items:
            items.append({
                "name": p.metadata.name,
                "namespace": p.metadata.namespace,
                "status": p.status.phase,
                "node": p.spec.node_name,
                "restarts": sum(c.restart_count for c in (p.status.container_statuses or [])),
                "ready": all(c.ready for c in (p.status.container_statuses or [])),
            })
        return {"success": True, "output": items}

    async def _describe_pod(self, params: dict) -> dict:
        ns = params.get("namespace", "default")
        pod_name = params["pod_name"]
        pod = self._api.read_namespaced_pod(pod_name, ns)
        return {"success": True, "output": str(pod)}

    async def _get_logs(self, params: dict) -> dict:
        ns = params.get("namespace", "default")
        pod_name = params["pod_name"]
        container = params.get("container")
        tail = params.get("tail_lines", 100)
        previous = params.get("previous", False)
        kwargs = {"namespace": ns, "name": pod_name, "tail_lines": tail}
        if container:
            kwargs["container"] = container
        if previous:
            kwargs["previous"] = True
        logs = self._api.read_namespaced_pod_log(**kwargs)
        return {"success": True, "output": logs}

    async def _get_events(self, params: dict) -> dict:
        if params.get("all_namespaces", False):
            events = self._api.list_event_for_all_namespaces()
        else:
            ns = params.get("namespace", "default")
            events = self._api.list_namespaced_event(ns)
        items = []
        for e in events.items:
            items.append({
                "type": e.type,
                "reason": e.reason,
                "message": e.message,
                "object": e.involved_object.name,
                "kind": e.involved_object.kind,
                "count": e.count,
                "last_ts": str(e.last_timestamp or ""),
            })
        return {"success": True, "output": items}

    async def _get_deployments(self, params: dict) -> dict:
        ns = params.get("namespace", "default")
        deps = self._apps.list_namespaced_deployment(ns)
        items = []
        for d in deps.items:
            items.append({
                "name": d.metadata.name,
                "replicas": d.spec.replicas,
                "available": d.status.available_replicas or 0,
                "ready": d.status.ready_replicas or 0,
            })
        return {"success": True, "output": items}

    async def _restart_deployment(self, params: dict) -> dict:
        ns = params.get("namespace", "default")
        name = params["name"]
        body = {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": str(__import__("datetime").datetime.now())}}}}}
        self._apps.patch_namespaced_deployment(name, ns, body)
        return {"success": True, "output": f"Restarted deployment {name}"}

    async def _scale_deployment(self, params: dict) -> dict:
        ns = params.get("namespace", "default")
        name = params["name"]
        replicas = params["replicas"]
        body = {"spec": {"replicas": replicas}}
        self._apps.patch_namespaced_deployment(name, ns, body)
        return {"success": True, "output": f"Scaled deployment {name} to {replicas}"}

    async def _delete_pod(self, params: dict) -> dict:
        ns = params.get("namespace", "default")
        name = params["pod_name"]
        self._api.delete_namespaced_pod(name, ns)
        return {"success": True, "output": f"Deleted pod {name}"}

    async def _get_nodes(self, params: dict) -> dict:
        nodes = self._api.list_node()
        items = []
        for n in nodes.items:
            items.append({
                "name": n.metadata.name,
                "status": next((c.status for c in n.status.conditions if c.type == "Ready"), "Unknown"),
                "kubelet": n.status.node_info.kubelet_version,
                "os": n.status.node_info.os_image,
                "pods": len([p for p in self._api.list_pod_for_all_namespaces().items if p.spec.node_name == n.metadata.name]),
            })
        return {"success": True, "output": items}

    async def _top_pod(self, params: dict) -> dict:
        ns = params.get("namespace", "default")
        try:
            metrics = client.CustomObjectsApi().list_namespaced_custom_object(
                group="metrics.k8s.io", version="v1beta1",
                namespace=ns, plural="pods",
            )
            items = []
            for item in metrics.get("items", []):
                containers = item.get("containers", [])
                cpu = sum(int(c["usage"].get("cpu", "0").rstrip("n")) for c in containers if "usage" in c)
                mem = sum(int(c["usage"].get("memory", "0").rstrip("Ki")) for c in containers if "usage" in c)
                items.append({
                    "name": item["metadata"]["name"],
                    "cpu_nano": cpu,
                    "mem_kib": mem,
                })
            return {"success": True, "output": items}
        except ApiException:
            return {"success": False, "error": "Metrics API not available (install metrics-server)"}
