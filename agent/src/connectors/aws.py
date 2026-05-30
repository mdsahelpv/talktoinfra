"""AWS connector using boto3."""

import boto3

from src.connectors.base import BaseConnector
from src.config import AgentConfig


class AWSConnector(BaseConnector):
    def __init__(self, cfg: AgentConfig):
        self._cfg = cfg
        self._available = False
        self._ec2 = None
        self._session = None

    async def initialize(self) -> None:
        try:
            kwargs = {"region_name": self._cfg.aws_region}
            if self._cfg.aws_access_key_id:
                kwargs["aws_access_key_id"] = self._cfg.aws_access_key_id
                kwargs["aws_secret_access_key"] = self._cfg.aws_secret_access_key
            self._session = boto3.Session(**kwargs)
            self._ec2 = self._session.client("ec2")
            self._available = True
        except Exception as e:
            print(f"[aws] Init failed: {e}")
            self._available = False

    @property
    def name(self) -> str:
        return "aws"

    @property
    def is_available(self) -> bool:
        return self._available

    async def health(self) -> dict:
        if not self._available:
            return {"healthy": False, "error": "Not initialized"}
        return {"healthy": True}

    async def execute(self, action: str, params: dict) -> dict:
        handlers = {
            "aws_list_ec2": self._list_ec2,
            "aws_describe_vpc": self._describe_vpc,
            "aws_start_instance": self._start_instance,
            "aws_stop_instance": self._stop_instance,
        }
        handler = handlers.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown AWS action: {action}"}
        return await handler(params)

    async def _list_ec2(self, params: dict) -> dict:
        filters = []
        if params.get("state"):
            filters.append({"Name": "instance-state-name", "Values": [params["state"]]})
        kwargs = {"Filters": filters} if filters else {}
        instances = self._ec2.describe_instances(**kwargs)
        items = []
        for r in instances.get("Reservations", []):
            for i in r.get("Instances", []):
                name = ""
                if i.get("Tags"):
                    for t in i["Tags"]:
                        if t["Key"] == "Name":
                            name = t["Value"]
                items.append({
                    "id": i["InstanceId"],
                    "name": name,
                    "state": i["State"]["Name"],
                    "type": i["InstanceType"],
                    "public_ip": i.get("PublicIpAddress", ""),
                    "private_ip": i.get("PrivateIpAddress", ""),
                    "launch_time": str(i["LaunchTime"]),
                })
        return {"success": True, "output": items}

    async def _describe_vpc(self, params: dict) -> dict:
        vpcs = self._ec2.describe_vpcs()
        items = []
        for v in vpcs.get("Vpcs", []):
            items.append({
                "id": v["VpcId"],
                "cidr": v.get("CidrBlock", ""),
                "state": v.get("State", ""),
                "default": v.get("IsDefault", False),
            })
        return {"success": True, "output": items}

    async def _start_instance(self, params: dict) -> dict:
        self._ec2.start_instances(InstanceIds=[params["instance_id"]])
        return {"success": True, "output": f"Starting instance {params['instance_id']}"}

    async def _stop_instance(self, params: dict) -> dict:
        self._ec2.stop_instances(InstanceIds=[params["instance_id"]])
        return {"success": True, "output": f"Stopping instance {params['instance_id']}"}
