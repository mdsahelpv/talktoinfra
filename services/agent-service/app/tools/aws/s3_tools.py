"""
AWS S3 tools for managing S3 buckets and objects.
"""

from typing import Any, Dict, List, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError

import structlog

logger = structlog.get_logger()


def get_s3_client(region: str = "us-east-1") -> Any:
    """Get an S3 client."""
    return boto3.client("s3", region_name=region)


async def list_s3_buckets(region: str = "us-east-1") -> Dict[str, Any]:
    """
    List all S3 buckets.

    Args:
        region: AWS region

    Returns:
        Dictionary with bucket list or error information
    """
    try:
        s3 = get_s3_client(region)
        response = s3.list_buckets()

        buckets = []
        for bucket in response.get("Buckets", []):
            buckets.append({
                "name": bucket.get("Name"),
                "creation_date": bucket.get("CreationDate").isoformat() if bucket.get("CreationDate") else None,
            })

        return {
            "success": True,
            "count": len(buckets),
            "buckets": buckets,
            "region": region,
        }

    except (ClientError, BotoCoreError) as e:
        logger.error("s3_list_buckets_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }

    except Exception as e:
        logger.error("s3_list_buckets_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def list_objects(
    bucket_name: str,
    prefix: str = "",
    max_keys: int = 1000,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    List objects in an S3 bucket.

    Args:
        bucket_name: S3 bucket name
        prefix: Prefix to filter objects
        max_keys: Maximum number of objects to return
        region: AWS region

    Returns:
        Dictionary with object list or error information
    """
    try:
        s3 = get_s3_client(region)

        kwargs = {
            "Bucket": bucket_name,
            "MaxKeys": max_keys,
        }
        if prefix:
            kwargs["Prefix"] = prefix

        response = s3.list_objects_v2(**kwargs)

        objects = []
        if "Contents" in response:
            for obj in response["Contents"]:
                objects.append({
                    "key": obj.get("Key"),
                    "size": obj.get("Size"),
                    "last_modified": obj.get("LastModified").isoformat() if obj.get("LastModified") else None,
                    "etag": obj.get("ETag"),
                    "storage_class": obj.get("StorageClass"),
                })

        return {
            "success": True,
            "bucket": bucket_name,
            "count": len(objects),
            "objects": objects,
            "is_truncated": response.get("IsTruncated", False),
            "next_continuation_token": response.get("NextContinuationToken"),
            "region": region,
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchBucket":
            return {
                "success": False,
                "error": f"Bucket '{bucket_name}' not found",
                "error_type": "NotFound",
            }
        logger.error("s3_list_objects_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": "ClientError",
        }

    except Exception as e:
        logger.error("s3_list_objects_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def upload_file(
    file_path: str,
    bucket_name: str,
    object_key: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    Upload a file to S3.

    Args:
        file_path: Local file path to upload
        bucket_name: S3 bucket name
        object_key: S3 object key
        region: AWS region

    Returns:
        Dictionary with operation result or error information
    """
    try:
        s3 = get_s3_client(region)

        s3.upload_file(file_path, bucket_name, object_key)

        return {
            "success": True,
            "message": f"File uploaded to s3://{bucket_name}/{object_key}",
            "bucket": bucket_name,
            "key": object_key,
            "region": region,
        }

    except (ClientError, BotoCoreError) as e:
        logger.error("s3_upload_file_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }

    except Exception as e:
        logger.error("s3_upload_file_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def download_file(
    bucket_name: str,
    object_key: str,
    file_path: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    Download a file from S3.

    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        file_path: Local file path to save to
        region: AWS region

    Returns:
        Dictionary with operation result or error information
    """
    try:
        s3 = get_s3_client(region)

        s3.download_file(bucket_name, object_key, file_path)

        return {
            "success": True,
            "message": f"File downloaded from s3://{bucket_name}/{object_key}",
            "bucket": bucket_name,
            "key": object_key,
            "local_path": file_path,
            "region": region,
        }

    except (ClientError, BotoCoreError) as e:
        logger.error("s3_download_file_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }

    except Exception as e:
        logger.error("s3_download_file_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}


async def get_object(
    bucket_name: str,
    object_key: str,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    Get an object from S3.

    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        region: AWS region

    Returns:
        Dictionary with object content or error information
    """
    try:
        s3 = get_s3_client(region)

        response = s3.get_object(Bucket=bucket_name, Key=object_key)

        return {
            "success": True,
            "bucket": bucket_name,
            "key": object_key,
            "content_length": response.get("ContentLength"),
            "content_type": response.get("ContentType"),
            "last_modified": response.get("LastModified").isoformat() if response.get("LastModified") else None,
            "etag": response.get("ETag"),
            "body": response["Body"].read().decode("utf-8"),
            "region": region,
        }

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return {
                "success": False,
                "error": f"Object '{object_key}' not found in bucket '{bucket_name}'",
                "error_type": "NotFound",
            }
        logger.error("s3_get_object_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "error_type": "ClientError",
        }

    except Exception as e:
        logger.error("s3_get_object_error", error=str(e))
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
