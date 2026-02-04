"""Cloud Provider Onboarding API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, SecretStr

import structlog

logger = structlog.get_logger()

router = APIRouter()


# AWS Models

class AWSClusterCreateRequest(BaseModel):
    """Request model for registering an AWS account."""

    name: str = Field(..., min_length=1, max_length=255)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[SecretStr] = None
    aws_role_arn: Optional[str] = Field(
        None, description="IAM Role ARN for cross-account access")
    external_id: Optional[str] = Field(
        None, description="External ID for IAM Role")
    regions: List[str] = Field(default_factory=lambda: ["us-east-1"])
    resource_types: List[str] = Field(
        default_factory=lambda: ["ec2", "rds", "s3", "elb", "eks"],
        description="Resource types to discover",
    )
    tags: Optional[Dict[str, str]] = None


class AWSClusterResponse(BaseModel):
    """Response model for AWS account."""

    id: str
    name: str
    provider: str = "aws"
    account_id: Optional[str]
    status: str
    regions: List[str]
    resource_types: List[str]
    created_at: datetime
    updated_at: datetime


# Azure Models

class AzureClusterCreateRequest(BaseModel):
    """Request model for registering an Azure subscription."""

    name: str = Field(..., min_length=1, max_length=255)
    subscription_id: str
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[SecretStr] = None
    resource_groups: List[str] = Field(default_factory=lambda: ["*"])
    resource_types: List[str] = Field(
        default_factory=lambda: ["vm", "storage", "sql", "aks"])
    use_managed_identity: bool = Field(default=False)
    tags: Optional[Dict[str, str]] = None


class AzureClusterResponse(BaseModel):
    """Response model for Azure subscription."""

    id: str
    name: str
    provider: str = "azure"
    subscription_id: str
    tenant_id: Optional[str]
    status: str
    resource_groups: List[str]
    created_at: datetime
    updated_at: datetime


# GCP Models

class GCPClusterCreateRequest(BaseModel):
    """Request model for registering a GCP project."""

    name: str = Field(..., min_length=1, max_length=255)
    project_id: str
    service_account_json: Optional[str] = Field(
        None, description="Base64-encoded service account JSON")
    service_account_email: Optional[str] = None
    regions: List[str] = Field(default_factory=lambda: ["us-central1"])
    resource_types: List[str] = Field(
        default_factory=lambda: ["compute", "gke", "cloud-sql", "storage"],
    )
    use_workload_identity: bool = Field(default=False)
    tags: Optional[Dict[str, str]] = None


class GCPClusterResponse(BaseModel):
    """Response model for GCP project."""

    id: str
    name: str
    provider: str = "gcp"
    project_id: str
    status: str
    regions: List[str]
    created_at: datetime
    updated_at: datetime


# In-memory storage
cloud_accounts_storage: Dict[str, Dict[str, Any]] = {}


# AWS Endpoints

@router.post("/aws/register", response_model=AWSClusterResponse, status_code=status.HTTP_201_CREATED)
async def register_aws_account(request: AWSClusterCreateRequest) -> AWSClusterResponse:
    """Register an AWS account for infrastructure discovery.

    Supports:
    - Access key + secret key
    - IAM Role ARN (for cross-account access)
    - AWS SSO (planned)

    Args:
        request: AWS registration request

    Returns:
        AWS account response

    """
    logger.info("registering_aws_account", name=request.name)

    account_id = str(uuid4())

    # Validate credentials
    if not request.aws_access_key_id or not request.aws_secret_access_key:
        if not request.aws_role_arn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either (aws_access_key_id + aws_secret_access_key) or aws_role_arn is required",
            )

    # TODO: Implement actual AWS validation
    # - Try boto3 sts.get_caller_identity()
    # - Test read-only permissions
    # - List available regions

    account = {
        "id": account_id,
        "name": request.name,
        "provider": "aws",
        "account_id": None,  # Will be populated after validation
        "status": "pending",
        "regions": request.regions,
        "resource_types": request.resource_types,
        "tags": request.tags or {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    cloud_accounts_storage[account_id] = account

    return AWSClusterResponse(
        id=account["id"],
        name=account["name"],
        provider=account["provider"],
        account_id=account["account_id"],
        status=account["status"],
        regions=account["regions"],
        resource_types=account["resource_types"],
        created_at=account["created_at"],
        updated_at=account["updated_at"],
    )


@router.get("/aws", response_model=List[AWSClusterResponse])
async def list_aws_accounts() -> List[AWSClusterResponse]:
    """List all registered AWS accounts."""
    return [
        AWSClusterResponse(
            id=a["id"],
            name=a["name"],
            provider=a["provider"],
            account_id=a.get("account_id"),
            status=a["status"],
            regions=a.get("regions", []),
            resource_types=a.get("resource_types", []),
            created_at=a["created_at"],
            updated_at=a["updated_at"],
        )
        for a in cloud_accounts_storage.values()
        if a["provider"] == "aws"
    ]


# Azure Endpoints

@router.post("/azure/register", response_model=AzureClusterResponse, status_code=status.HTTP_201_CREATED)
async def register_azure_subscription(request: AzureClusterCreateRequest) -> AzureClusterResponse:
    """Register an Azure subscription for infrastructure discovery.

    Supports:
    - Service Principal (client ID + secret)
    - Managed Identity (for AKS)
    - Azure CLI (development only)

    Args:
        request: Azure registration request

    Returns:
        Azure subscription response

    """
    logger.info("registering_azure_subscription", name=request.name,
                subscription_id=request.subscription_id)

    account_id = str(uuid4())

    if not request.client_id or not request.client_secret:
        if not request.use_managed_identity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either (client_id + client_secret) or use_managed_identity is required",
            )

    # TODO: Implement actual Azure validation
    # - Try azure-mgmt-resource operations
    # - Test read permissions

    account = {
        "id": account_id,
        "name": request.name,
        "provider": "azure",
        "subscription_id": request.subscription_id,
        "tenant_id": request.tenant_id,
        "status": "pending",
        "resource_groups": request.resource_groups,
        "resource_types": request.resource_types,
        "use_managed_identity": request.use_managed_identity,
        "tags": request.tags or {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    cloud_accounts_storage[account_id] = account

    return AzureClusterResponse(
        id=account["id"],
        name=account["name"],
        provider=account["provider"],
        subscription_id=account["subscription_id"],
        tenant_id=account.get("tenant_id"),
        status=account["status"],
        resource_groups=account["resource_groups"],
        created_at=account["created_at"],
        updated_at=account["updated_at"],
    )


@router.get("/azure", response_model=List[AzureClusterResponse])
async def list_azure_subscriptions() -> List[AzureClusterResponse]:
    """List all registered Azure subscriptions."""
    return [
        AzureClusterResponse(
            id=a["id"],
            name=a["name"],
            provider=a["provider"],
            subscription_id=a["subscription_id"],
            tenant_id=a.get("tenant_id"),
            status=a["status"],
            resource_groups=a.get("resource_groups", []),
            created_at=a["created_at"],
            updated_at=a["updated_at"],
        )
        for a in cloud_accounts_storage.values()
        if a["provider"] == "azure"
    ]


# GCP Endpoints

@router.post("/gcp/register", response_model=GCPClusterResponse, status_code=status.HTTP_201_CREATED)
async def register_gcp_project(request: GCPClusterCreateRequest) -> GCPClusterResponse:
    """Register a GCP project for infrastructure discovery.

    Supports:
    - Service Account JSON key
    - Workload Identity (for GKE)
    - Application Default Credentials (development)

    Args:
        request: GCP registration request

    Returns:
        GCP project response

    """
    logger.info("registering_gcp_project", name=request.name,
                project_id=request.project_id)

    account_id = str(uuid4())

    if not request.service_account_json:
        if not request.use_workload_identity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either service_account_json or use_workload_identity is required",
            )

    # TODO: Implement actual GCP validation
    # - Try google.cloud.resourcemanager.projects.get()
    # - Test read permissions

    account = {
        "id": account_id,
        "name": request.name,
        "provider": "gcp",
        "project_id": request.project_id,
        "status": "pending",
        "regions": request.regions,
        "resource_types": request.resource_types,
        "use_workload_identity": request.use_workload_identity,
        "tags": request.tags or {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    cloud_accounts_storage[account_id] = account

    return GCPClusterResponse(
        id=account["id"],
        name=account["name"],
        provider=account["provider"],
        project_id=account["project_id"],
        status=account["status"],
        regions=account["regions"],
        created_at=account["created_at"],
        updated_at=account["updated_at"],
    )


@router.get("/gcp", response_model=List[GCPClusterResponse])
async def list_gcp_projects() -> List[GCPClusterResponse]:
    """List all registered GCP projects."""
    return [
        GCPClusterResponse(
            id=a["id"],
            name=a["name"],
            provider=a["provider"],
            project_id=a["project_id"],
            status=a["status"],
            regions=a.get("regions", []),
            created_at=a["created_at"],
            updated_at=a["updated_at"],
        )
        for a in cloud_accounts_storage.values()
        if a["provider"] == "gcp"
    ]


# Cloud connection test

class CloudConnectionTestResponse(BaseModel):
    """Response model for cloud connection test."""

    provider: str
    account_id: str
    success: bool
    message: str
    regions: List[str]
    tested_at: datetime


@router.post("/{provider}/{account_id}/test-connection", response_model=CloudConnectionTestResponse)
async def test_cloud_connection(provider: str, account_id: str) -> CloudConnectionTestResponse:
    """Test cloud provider connection.

    Args:
        provider: Cloud provider (aws, azure, gcp)
        account_id: Account/Project ID

    Returns:
        Connection test result

    """
    if account_id not in cloud_accounts_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{provider} account {account_id} not found",
        )

    account = cloud_accounts_storage[account_id]

    logger.info("testing_cloud_connection",
                provider=provider, account_id=account_id)

    # TODO: Implement actual cloud connection tests
    # - AWS: boto3 sts.get_caller_identity()
    # - Azure: azure-mgmt-resource operations
    # - GCP: cloudresourcemanager.projects.get()

    return CloudConnectionTestResponse(
        provider=provider,
        account_id=account_id,
        success=True,
        message="Connection successful",
        regions=account.get("regions", []),
        tested_at=datetime.utcnow(),
    )


@router.delete("/{provider}/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cloud_account(provider: str, account_id: str):
    """Delete a cloud account registration.

    Args:
        provider: Cloud provider
        account_id: Account ID

    """
    if account_id not in cloud_accounts_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{provider} account {account_id} not found",
        )

    logger.info("deleting_cloud_account",
                provider=provider, account_id=account_id)

    # TODO: Revoke credentials from Vault
    del cloud_accounts_storage[account_id]
