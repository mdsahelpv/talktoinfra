"""
AWS EC2 tools for managing EC2 instances.
"""

from typing import Any, Dict, List, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError

import structlog

logger = structlog.get_logger()


def get_ec2_client(region: str = "us-east-1") -> Any:
    """Get an EC2 client for the specified region."""
    return boto3.client("ec2", region_name=region)


async def list_ec2_instances(
    region: str = "us-east-1",
    filters: Optional[List[Dict[str, Any]]] = None,
    max_results: int = 100,
) -> Dict[str, Any]:
    """
    List EC2 instances in a region.

    Args:
        region: AWS region
        filters: Optional filters for the instances
        max_results: Maximum number of results to return

    Returns:
        Dictionary with instance list or error information
    """
    try:
        ec2 = get_ec2_client(region)

        kwargs = {"MaxResults": max_results}
        if filters:
            kwargs["Filters"] = filters

        response = ec2.describe_instances(**kwargs)

        instances = []
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instances.append({
                    "instance_id": instance.get("InstanceId"),
                    "instance_type": instance.get("InstanceType"),
                    "state": instance.get("State", {}).get("Name"),
                    "private_ip": instance.get("PrivateIpAddress"),
                    "public_ip": instance.get("PublicIpAddress"),
                    "private_dns": instance.get("PrivateDnsName"),
                    "public_dns": instance.get("PublicDnsName"),
                    "vpc_id": instance.get("VpcId"),
                    "subnet_id": instance.get("SubnetId"),
                    "tags": instance.get("Tags", []),
                    "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
                    "architecture": instance.get("Architecture"),
                    "root_device_type": instance.get("RootDeviceType"),
                })

        return {
            "success": True,
            "count": len(instances),
            "instances": instances,
            "region": region,
        }

    except (ClientError, BotoCoreError) as e:
        logger.error("ec2_list_instances_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }

    except Exception as e:
        logger.error("ec2_list_instances_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def describe_ec2_instance(
    instance_id: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    Get detailed information about an EC2 instance.

    Args:
        instance_id: EC2 instance ID
        region: AWS region

    Returns:
        Dictionary with instance details or error information
    """
    try:
        ec2 = get_ec2_client(region)

        response = ec2.describe_instances(InstanceIds=[instance_id])

        reservations = response.get("Reservations", [])
        if not reservations:
            return {
                "success": False,
                "error": f"Instance '{instance_id}' not found",
                "error_type": "NotFound",
            }

        instance = reservations[0].get("Instances", [])[0]

        # Get detailed instance information
        instance_info = {
            "instance_id": instance.get("InstanceId"),
            "instance_type": instance.get("InstanceType"),
            "state": instance.get("State", {}).get("Name"),
            "state_reason": instance.get("StateReason", {}).get("Message"),
            "private_ip": instance.get("PrivateIpAddress"),
            "public_ip": instance.get("PublicIpAddress"),
            "private_dns": instance.get("PrivateDnsName"),
            "public_dns": instance.get("PublicDnsName"),
            "vpc_id": instance.get("VpcId"),
            "subnet_id": instance.get("SubnetId"),
            "security_groups": [
                {"group_id": sg.get("GroupId"), "group_name": sg.get("GroupName")}
                for sg in instance.get("SecurityGroups", [])
            ],
            "tags": instance.get("Tags", []),
            "launch_time": instance.get("LaunchTime").isoformat() if instance.get("LaunchTime") else None,
            "architecture": instance.get("Architecture"),
            "root_device_type": instance.get("RootDeviceType"),
            "root_device_name": instance.get("RootDeviceName"),
            "ebs_optimized": instance.get("EbsOptimized"),
            "ena_support": instance.get("EnaSupport"),
            "hypervisor": instance.get("Hypervisor"),
            "iam_instance_profile": instance.get("IamInstanceProfile", {}).get("Arn"),
            "monitoring": instance.get("Monitoring", {}).get("State"),
            "placement": instance.get("Placement", {}),
            "product_codes": instance.get("ProductCodes", []),
        }

        # Get block device mappings
        block_devices = []
        for bd in instance.get("BlockDeviceMappings", []):
            block_devices.append({
                "device_name": bd.get("DeviceName"),
                "ebs_volume_id": bd.get("Ebs", {}).get("VolumeId"),
                "status": bd.get("Ebs", {}).get("Status"),
            })
        instance_info["block_devices"] = block_devices

        return {
            "success": True,
            "instance": instance_info,
            "region": region,
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
            return {
                "success": False,
                "error": f"Instance '{instance_id}' not found",
                "error_type": "NotFound",
            }
        logger.error("ec2_describe_instance_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": "ClientError",
        }

    except Exception as e:
        logger.error("ec2_describe_instance_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def start_ec2_instance(
    instance_id: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    Start an EC2 instance.

    Args:
        instance_id: EC2 instance ID
        region: AWS region

    Returns:
        Dictionary with operation result or error information
    """
    try:
        ec2 = get_ec2_client(region)

        response = ec2.start_instances(InstanceIds=[instance_id])

        return {
            "success": True,
            "message": f"Instance '{instance_id}' start initiated",
            "current_state": response["StartingInstances"][0]["CurrentState"]["Name"],
            "previous_state": response["StartingInstances"][0]["PreviousState"]["Name"],
            "instance_id": instance_id,
            "region": region,
        }

    except ClientError as e:
        logger.error("ec2_start_instance_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": "ClientError",
        }

    except Exception as e:
        logger.error("ec2_start_instance_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def stop_ec2_instance(
    instance_id: str,
    region: str = "us-east-1",
    force: bool = False,
) -> Dict[str, Any]:
    """
    Stop an EC2 instance.

    Args:
        instance_id: EC2 instance ID
        region: AWS region
        force: Force stop (ignore shutdown behavior)

    Returns:
        Dictionary with operation result or error information
    """
    try:
        ec2 = get_ec2_client(region)

        kwargs = {"InstanceIds": [instance_id]}
        if force:
            kwargs["Force"] = True

        response = ec2.stop_instances(**kwargs)

        return {
            "success": True,
            "message": f"Instance '{instance_id}' stop initiated",
            "current_state": response["StoppingInstances"][0]["CurrentState"]["Name"],
            "previous_state": response["StoppingInstances"][0]["PreviousState"]["Name"],
            "instance_id": instance_id,
            "region": region,
        }

    except ClientError as e:
        logger.error("ec2_stop_instance_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": "ClientError",
        }

    except Exception as e:
        logger.error("ec2_stop_instance_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def terminate_ec2_instance(
    instance_id: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    Terminate an EC2 instance.

    Args:
        instance_id: EC2 instance ID
        region: AWS region

    Returns:
        Dictionary with operation result or error information
    """
    try:
        ec2 = get_ec2_client(region)

        response = ec2.terminate_instances(InstanceIds=[instance_id])

        return {
            "success": True,
            "message": f"Instance '{instance_id}' termination initiated",
            "current_state": response["TerminatingInstances"][0]["CurrentState"]["Name"],
            "previous_state": response["TerminatingInstances"][0]["PreviousState"]["Name"],
            "instance_id": instance_id,
            "region": region,
        }

    except ClientError as e:
        logger.error("ec2_terminate_instance_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": "ClientError",
        }

    except Exception as e:
        logger.error("ec2_terminate_instance_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
