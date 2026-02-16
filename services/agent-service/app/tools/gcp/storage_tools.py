"""
Google Cloud Storage (GCS) Tools

Provides tools for managing Google Cloud Storage buckets and objects.
"""

from typing import Any, Dict, List, Optional
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError
import structlog


logger = structlog.get_logger()


def get_gcs_client() -> storage.Client:
    """Get GCS Client.

    Returns:
        storage.Client instance
    """
    return storage.Client()


async def list_buckets(
    project_id: str,
) -> List[Dict[str, Any]]:
    """List Google Cloud Storage buckets.

    Args:
        project_id: GCP project ID

    Returns:
        List of bucket information dictionaries
    """
    try:
        client = get_gcs_client()
        
        buckets = client.list_buckets(project=project_id)
        
        result = []
        for bucket in buckets:
            result.append({
                "name": bucket.name,
                "location": bucket.location,
                "location_type": bucket.location_type,
                "storage_class": bucket.storage_class,
                "time_created": bucket.time_created.isoformat() if bucket.time_created else None,
                "updated": bucket.updated.isoformat() if bucket.updated else None,
                " versioning_enabled": bucket.versioning_enabled if hasattr(bucket, 'versioning_enabled') else False,
                "public_access_prevention": bucket.public_access_prevention if hasattr(bucket, 'public_access_prevention') else None,
            })

        logger.info("gcs_buckets_listed", count=len(result), project_id=project_id)
        return result

    except GoogleAPIError as e:
        logger.error("gcs_list_buckets_failed", error=str(e))
        raise


async def list_objects(
    project_id: str,
    bucket_name: str,
    prefix: Optional[str] = None,
    delimiter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List objects in a GCS bucket.

    Args:
        project_id: GCP project ID
        bucket_name: Bucket name
        prefix: Optional prefix to filter objects
        delimiter: Optional delimiter for hierarchical listing

    Returns:
        List of object information dictionaries
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        
        blobs = bucket.list_blobs(prefix=prefix, delimiter=delimiter)
        
        result = []
        for blob in blobs:
            result.append({
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "md5_hash": blob.md5_hash,
                "crc32c": blob.crc32c,
            })

        logger.info("gcs_objects_listed", count=len(result), bucket_name=bucket_name)
        return result

    except GoogleAPIError as e:
        logger.error("gcs_list_objects_failed", error=str(e))
        raise


async def upload_object(
    project_id: str,
    bucket_name: str,
    object_name: str,
    data: str,
    content_type: str = "text/plain",
) -> Dict[str, Any]:
    """Upload an object to GCS.

    Args:
        project_id: GCP project ID
        bucket_name: Bucket name
        object_name: Object name
        data: Data to upload (string)
        content_type: Content type

    Returns:
        Upload result dictionary
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        
        blob.upload_from_string(data, content_type=content_type)
        
        result = {
            "status": "uploaded",
            "object_name": object_name,
            "bucket_name": bucket_name,
            "size": len(data),
        }

        logger.info("gcs_object_uploaded", object_name=object_name, bucket_name=bucket_name)
        return result

    except GoogleAPIError as e:
        logger.error("gcs_upload_object_failed", error=str(e))
        raise


async def download_object(
    project_id: str,
    bucket_name: str,
    object_name: str,
) -> Dict[str, Any]:
    """Download an object from GCS.

    Args:
        project_id: GCP project ID
        bucket_name: Bucket name
        object_name: Object name

    Returns:
        Downloaded object data dictionary
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        
        data = blob.download_as_string()
        
        result = {
            "object_name": object_name,
            "bucket_name": bucket_name,
            "data": data.decode("utf-8"),
            "size": len(data),
        }

        logger.info("gcs_object_downloaded", object_name=object_name, bucket_name=bucket_name)
        return result

    except GoogleAPIError as e:
        logger.error("gcs_download_object_failed", error=str(e))
        raise


async def delete_object(
    project_id: str,
    bucket_name: str,
    object_name: str,
) -> Dict[str, Any]:
    """Delete an object from GCS.

    Args:
        project_id: GCP project ID
        bucket_name: Bucket name
        object_name: Object name

    Returns:
        Delete result dictionary
    """
    try:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        
        blob.delete()
        
        result = {
            "status": "deleted",
            "object_name": object_name,
            "bucket_name": bucket_name,
        }

        logger.info("gcs_object_deleted", object_name=object_name, bucket_name=bucket_name)
        return result

    except GoogleAPIError as e:
        logger.error("gcs_delete_object_failed", error=str(e))
        raise
