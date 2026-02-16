"""
Azure Storage Tools

Provides tools for managing Azure Storage accounts and blobs.
"""

from typing import Any, Dict, List, Optional
from azure.identity import DefaultAzureCredential
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.core.exceptions import AzureError
import structlog


logger = structlog.get_logger()


def get_azure_storage_client(subscription_id: str) -> StorageManagementClient:
    """Get Azure Storage Management Client.

    Args:
        subscription_id: Azure subscription ID

    Returns:
        StorageManagementClient instance
    """
    credential = DefaultAzureCredential()
    return StorageManagementClient(credential, subscription_id)


async def list_storage_accounts(
    subscription_id: str,
    resource_group: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List Azure Storage Accounts.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Optional resource group name to filter by

    Returns:
        List of storage account information dictionaries
    """
    try:
        client = get_azure_storage_client(subscription_id)
        
        if resource_group:
            accounts = client.storage_accounts.list_by_resource_group(resource_group_name=resource_group)
        else:
            accounts = client.storage_accounts.list()
        
        result = []
        for account in accounts:
            result.append({
                "id": account.id,
                "name": account.name,
                "resource_group": account.id.split("/")[4],
                "location": account.location,
                "sku_tier": account.sku.tier.value if account.sku else None,
                "sku_name": account.sku.name.value if account.sku else None,
                "account_kind": account.kind.value if account.kind else None,
                "provisioning_state": account.provisioning_state,
                "primary_endpoints": {
                    "blob": account.primary_endpoints.blob if account.primary_endpoints else None,
                    "queue": account.primary_endpoints.queue if account.primary_endpoints else None,
                    "table": account.primary_endpoints.table if account.primary_endpoints else None,
                    "file": account.primary_endpoints.file if account.primary_endpoints else None,
                } if account.primary_endpoints else None,
                "enable_https_traffic_only": account.enable_https_traffic_only,
                "tags": account.tags or {},
            })

        logger.info("azure_storage_accounts_listed", count=len(result), subscription_id=subscription_id)
        return result

    except AzureError as e:
        logger.error("azure_list_storage_accounts_failed", error=str(e))
        raise


async def list_storage_containers(
    subscription_id: str,
    resource_group: str,
    storage_account: str,
) -> List[Dict[str, Any]]:
    """List containers in an Azure Storage Account.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        storage_account: Storage account name

    Returns:
        List of container information dictionaries
    """
    try:
        # Get connection string
        client = get_azure_storage_client(subscription_id)
        keys = client.storage_accounts.list_keys(resource_group_name=resource_group, account_name=storage_account)
        conn_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account};AccountKey={keys.keys[0].value};EndpointSuffix=core.windows.net"
        
        # List containers
        blob_service = BlobServiceClient.from_connection_string(conn_string)
        containers = blob_service.list_containers()
        
        result = []
        for container in containers:
            result.append({
                "name": container.name,
                "url": container.url,
                "last_modified": container.last_modified.isoformat() if container.last_modified else None,
                "public_access": container.public_access if hasattr(container, 'public_access') else None,
            })

        logger.info("azure_storage_containers_listed", count=len(result), storage_account=storage_account)
        return result

    except AzureError as e:
        logger.error("azure_list_storage_containers_failed", error=str(e))
        raise


async def list_blobs(
    subscription_id: str,
    resource_group: str,
    storage_account: str,
    container_name: str,
    prefix: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List blobs in an Azure Storage Container.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        storage_account: Storage account name
        container_name: Container name
        prefix: Optional prefix to filter blobs

    Returns:
        List of blob information dictionaries
    """
    try:
        # Get connection string
        client = get_azure_storage_client(subscription_id)
        keys = client.storage_accounts.list_keys(resource_group_name=resource_group, account_name=storage_account)
        conn_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account};AccountKey={keys.keys[0].value};EndpointSuffix=core.windows.net"
        
        # List blobs
        blob_service = BlobServiceClient.from_connection_string(conn_string)
        container = blob_service.get_container_client(container_name)
        blobs = container.list_blobs(name_starts_with=prefix)
        
        result = []
        for blob in blobs:
            result.append({
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
                "etag": blob.etag,
            })

        logger.info("azure_blobs_listed", count=len(result), container_name=container_name)
        return result

    except AzureError as e:
        logger.error("azure_list_blobs_failed", error=str(e))
        raise


async def upload_blob(
    subscription_id: str,
    resource_group: str,
    storage_account: str,
    container_name: str,
    blob_name: str,
    data: str,
    content_type: str = "text/plain",
) -> Dict[str, Any]:
    """Upload a blob to Azure Storage.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        storage_account: Storage account name
        container_name: Container name
        blob_name: Blob name
        data: Data to upload (string)
        content_type: Content type

    Returns:
        Upload result dictionary
    """
    try:
        # Get connection string
        client = get_azure_storage_client(subscription_id)
        keys = client.storage_accounts.list_keys(resource_group_name=resource_group, account_name=storage_account)
        conn_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account};AccountKey={keys.keys[0].value};EndpointSuffix=core.windows.net"
        
        # Upload blob
        blob_service = BlobServiceClient.from_connection_string(conn_string)
        blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
        blob_client.upload_blob(data, overwrite=True, content_settings={"content_type": content_type})
        
        result = {
            "status": "uploaded",
            "blob_name": blob_name,
            "container_name": container_name,
            "size": len(data),
        }

        logger.info("azure_blob_uploaded", blob_name=blob_name, container_name=container_name)
        return result

    except AzureError as e:
        logger.error("azure_upload_blob_failed", error=str(e))
        raise


async def download_blob(
    subscription_id: str,
    resource_group: str,
    storage_account: str,
    container_name: str,
    blob_name: str,
) -> Dict[str, Any]:
    """Download a blob from Azure Storage.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        storage_account: Storage account name
        container_name: Container name
        blob_name: Blob name

    Returns:
        Downloaded blob data dictionary
    """
    try:
        # Get connection string
        client = get_azure_storage_client(subscription_id)
        keys = client.storage_accounts.list_keys(resource_group_name=resource_group, account_name=storage_account)
        conn_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account};AccountKey={keys.keys[0].value};EndpointSuffix=core.windows.net"
        
        # Download blob
        blob_service = BlobServiceClient.from_connection_string(conn_string)
        blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
        data = blob_client.download_blob().readall()
        
        result = {
            "blob_name": blob_name,
            "container_name": container_name,
            "data": data.decode("utf-8"),
            "size": len(data),
        }

        logger.info("azure_blob_downloaded", blob_name=blob_name, container_name=container_name)
        return result

    except AzureError as e:
        logger.error("azure_download_blob_failed", error=str(e))
        raise


async def delete_blob(
    subscription_id: str,
    resource_group: str,
    storage_account: str,
    container_name: str,
    blob_name: str,
) -> Dict[str, Any]:
    """Delete a blob from Azure Storage.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
        storage_account: Storage account name
        container_name: Container name
        blob_name: Blob name

    Returns:
        Delete result dictionary
    """
    try:
        # Get connection string
        client = get_azure_storage_client(subscription_id)
        keys = client.storage_accounts.list_keys(resource_group_name=resource_group, account_name=storage_account)
        conn_string = f"DefaultEndpointsProtocol=https;AccountName={storage_account};AccountKey={keys.keys[0].value};EndpointSuffix=core.windows.net"
        
        # Delete blob
        blob_service = BlobServiceClient.from_connection_string(conn_string)
        blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
        blob_client.delete_blob()
        
        result = {
            "status": "deleted",
            "blob_name": blob_name,
            "container_name": container_name,
        }

        logger.info("azure_blob_deleted", blob_name=blob_name, container_name=container_name)
        return result

    except AzureError as e:
        logger.error("azure_delete_blob_failed", error=str(e))
        raise
