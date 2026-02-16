"""
AWS tools package.
"""

# EC2 tools
from app.tools.aws.ec2_tools import (
    list_ec2_instances,
    describe_ec2_instance,
    start_ec2_instance,
    stop_ec2_instance,
    terminate_ec2_instance,
)

# S3 tools
from app.tools.aws.s3_tools import (
    list_s3_buckets,
    list_objects,
    upload_file,
    download_file,
)

# CloudWatch tools
from app.tools.aws.cloudwatch_tools import (
    get_metric_data,
    list_metrics,
    get_logs,
)

# EKS tools
from app.tools.aws.eks_tools import (
    list_eks_clusters,
    describe_eks_cluster,
    list_eks_node_groups,
)

__all__ = [
    # EC2
    "list_ec2_instances",
    "describe_ec2_instance",
    "start_ec2_instance",
    "stop_ec2_instance",
    "terminate_ec2_instance",
    # S3
    "list_s3_buckets",
    "list_objects",
    "upload_file",
    "download_file",
    # CloudWatch
    "get_metric_data",
    "list_metrics",
    "get_logs",
    # EKS
    "list_eks_clusters",
    "describe_eks_cluster",
    "list_eks_node_groups",
]
