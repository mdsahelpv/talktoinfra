"""
AWS EKS tools for managing EKS clusters.
"""

from typing import Any, Dict, List, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError

import structlog

logger = structlog.get_logger()


def get_eks_client(region: str = "us-east-1") -> Any:
    """Get an EKS client."""
    return boto3.client("eks", region_name=region)


async def list_eks_clusters(region: str = "us-east-1") -> Dict[str, Any]:
    """
    List all EKS clusters in a region.

    Args:
        region: AWS region

    Returns:
        Dictionary with cluster list or error information
    """
    try:
        eks = get_eks_client(region)

        response = eks.list_clusters()

        clusters = []
        for name in response.get("clusters", []):
            clusters.append({"name": name})

        return {
            "success": True,
            "count": len(clusters),
            "clusters": clusters,
            "region": region,
        }

    except (ClientError, BotoCoreError) as e:
        logger.error("eks_list_clusters_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }

    except Exception as e:
        logger.error("eks_list_clusters_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def describe_eks_cluster(
    cluster_name: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    Get detailed information about an EKS cluster.

    Args:
        cluster_name: EKS cluster name
        region: AWS region

    Returns:
        Dictionary with cluster details or error information
    """
    try:
        eks = get_eks_client(region)

        response = eks.describe_cluster(name=cluster_name)

        cluster = response.get("cluster", {})

        cluster_info = {
            "name": cluster.get("name"),
            "arn": cluster.get("arn"),
            "version": cluster.get("version"),
            "status": cluster.get("status"),
            "endpoint": cluster.get("endpoint"),
            "role_arn": cluster.get("roleArn"),
            "resources_vpc_config": cluster.get("resourcesVpcConfig"),
            "kubernetes_network_config": cluster.get("kubernetesNetworkConfig"),
            "logging": cluster.get("logging"),
            "identity": cluster.get("identity"),
            "platform_version": cluster.get("platformVersion"),
            "tags": cluster.get("tags", {}),
            "cluster_security_group_id": cluster.get("clusterSecurityGroupId"),
            "encryption_config": cluster.get("encryptionConfig"),
            "connector_config": cluster.get("connectorConfig"),
        }

        return {
            "success": True,
            "cluster": cluster_info,
            "region": region,
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return {
                "success": False,
                "error": f"Cluster '{cluster_name}' not found",
                "error_type": "NotFound",
            }
        logger.error("eks_describe_cluster_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": "ClientError",
        }

    except Exception as e:
        logger.error("eks_describe_cluster_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def list_eks_node_groups(
    cluster_name: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    List node groups in an EKS cluster.

    Args:
        cluster_name: EKS cluster name
        region: AWS region

    Returns:
        Dictionary with node group list or error information
    """
    try:
        eks = get_eks_client(region)

        response = eks.list_nodegroups(clusterName=cluster_name)

        node_groups = []
        for name in response.get("nodegroups", []):
            # Get details for each node group
            try:
                ng_response = eks.describe_nodegroup(
                    clusterName=cluster_name,
                    nodegroupName=name,
                )
                ng = ng_response.get("nodegroup", {})
                node_groups.append({
                    "name": ng.get("nodegroupName"),
                    "arn": ng.get("nodegroupArn"),
                    "cluster_name": ng.get("clusterName"),
                    "version": ng.get("version"),
                    "status": ng.get("status"),
                    "instance_types": ng.get("instanceTypes"),
                    "scaling_config": ng.get("scalingConfig"),
                    "ami_type": ng.get("amiType"),
                    "node_role": ng.get("nodeRole"),
                    "labels": ng.get("labels", {}),
                    "taints": ng.get("taints", []),
                })
            except Exception:
                node_groups.append({"name": name})

        return {
            "success": True,
            "cluster": cluster_name,
            "count": len(node_groups),
            "node_groups": node_groups,
            "region": region,
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return {
                "success": False,
                "error": f"Cluster '{cluster_name}' not found",
                "error_type": "NotFound",
            }
        logger.error("eks_list_nodegroups_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": "ClientError",
        }

    except Exception as e:
        logger.error("eks_list_nodegroups_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def list_eks_fargate_profiles(
    cluster_name: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    List Fargate profiles in an EKS cluster.

    Args:
        cluster_name: EKS cluster name
        region: AWS region

    Returns:
        Dictionary with Fargate profile list or error information
    """
    try:
        eks = get_eks_client(region)

        response = eks.list_fargate_profiles(clusterName=cluster_name)

        profiles = []
        for name in response.get("fargateProfileNames", []):
            profiles.append({"name": name})

        return {
            "success": True,
            "cluster": cluster_name,
            "count": len(profiles),
            "fargate_profiles": profiles,
            "region": region,
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return {
                "success": False,
                "error": f"Cluster '{cluster_name}' not found",
                "error_type": "NotFound",
            }
        logger.error("eks_list_fargate_profiles_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": "ClientError",
        }

    except Exception as e:
        logger.error("eks_list_fargate_profiles_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
