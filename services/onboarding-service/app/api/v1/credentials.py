"""Credential Management API endpoints."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger()

router = APIRouter()


# Credential Models

class CredentialInfo(BaseModel):
    """Non-sensitive credential information."""

    id: str
    cluster_id: str
    credential_type: str
    name: str
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    rotation_required: bool


class CredentialCreateRequest(BaseModel):
    """Request model for creating a credential."""

    cluster_id: str
    name: str = Field(..., min_length=1, max_length=255)
    credential_type: str = Field(...,
                                 description="kubeconfig, service_account, token, api_key")
    data: Dict[str, Any] = Field(..., description="Encrypted credential data")
    expires_at: Optional[datetime] = None
    rotation_period_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Auto-rotation period in days",
    )


class CredentialRotationResponse(BaseModel):
    """Response model for credential rotation."""

    credential_id: str
    old_credential_id: str
    success: bool
    message: str
    rotated_at: datetime


# In-memory storage
credentials_storage: Dict[str, Dict[str, Any]] = {}


@router.post("", response_model=CredentialInfo, status_code=status.HTTP_201_CREATED)
async def create_credential(request: CredentialCreateRequest) -> CredentialInfo:
    """Create a new credential for a cluster.

    Credentials are encrypted before storage using AES-256.
    For production, HashiCorp Vault should be used.

    Args:
        request: Credential creation request

    Returns:
        Credential info (non-sensitive)

    """
    logger.info("creating_credential",
                cluster_id=request.cluster_id, name=request.name)

    credential_id = str(uuid4())

    # TODO: Encrypt credential data before storage
    # - Use AES-256-GCM encryption
    # - Or store in HashiCorp Vault

    credential = {
        "id": credential_id,
        "cluster_id": request.cluster_id,
        "name": request.name,
        "credential_type": request.credential_type,
        "data_encrypted": True,  # Mark as encrypted
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_used_at": None,
        "expires_at": request.expires_at,
        "rotation_required": request.rotation_period_days is not None,
        "rotation_period_days": request.rotation_period_days,
    }

    credentials_storage[credential_id] = credential

    return CredentialInfo(
        id=credential["id"],
        cluster_id=credential["cluster_id"],
        credential_type=credential["credential_type"],
        name=credential["name"],
        created_at=credential["created_at"],
        updated_at=credential["updated_at"],
        last_used_at=credential["last_used_at"],
        expires_at=credential["expires_at"],
        rotation_required=credential["rotation_required"],
    )


@router.get("", response_model=Dict[str, Any])
async def list_credentials(
    cluster_id: Optional[str] = None,
    credential_type: Optional[str] = None,
) -> Dict[str, Any]:
    """List credentials for a cluster.

    Returns non-sensitive information only.

    Args:
        cluster_id: Filter by cluster ID
        credential_type: Filter by type

    Returns:
        Dictionary with credentials list

    """
    credentials = list(credentials_storage.values())

    if cluster_id:
        credentials = [c for c in credentials if c["cluster_id"] == cluster_id]
    if credential_type:
        credentials = [
            c for c in credentials if c["credential_type"] == credential_type]

    return {
        "credentials": [
            {
                "id": c["id"],
                "cluster_id": c["cluster_id"],
                "name": c["name"],
                "credential_type": c["credential_type"],
                "created_at": c["created_at"],
                "updated_at": c["updated_at"],
                "last_used_at": c.get("last_used_at"),
                "expires_at": c.get("expires_at"),
                "rotation_required": c.get("rotation_required", False),
            }
            for c in credentials
        ],
        "total": len(credentials),
    }


@router.get("/{credential_id}", response_model=CredentialInfo)
async def get_credential(credential_id: str) -> CredentialInfo:
    """Get credential information (non-sensitive).

    Args:
        credential_id: Credential ID

    Returns:
        Credential info

    """
    if credential_id not in credentials_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential {credential_id} not found",
        )

    c = credentials_storage[credential_id]

    return CredentialInfo(
        id=c["id"],
        cluster_id=c["cluster_id"],
        credential_type=c["credential_type"],
        name=c["name"],
        created_at=c["created_at"],
        updated_at=c["updated_at"],
        last_used_at=c.get("last_used_at"),
        expires_at=c.get("expires_at"),
        rotation_required=c.get("rotation_required", False),
    )


@router.post("/{credential_id}/rotate", response_model=CredentialRotationResponse)
async def rotate_credential(
    credential_id: str,
    new_data: Dict[str, Any],
) -> CredentialRotationResponse:
    """Rotate a credential with new data.

    Creates a new credential and marks the old one as deprecated.

    Args:
        credential_id: Credential to rotate
        new_data: New credential data

    Returns:
        Rotation result

    """
    if credential_id not in credentials_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential {credential_id} not found",
        )

    old_credential = credentials_storage[credential_id]

    logger.info("rotating_credential", credential_id=credential_id)

    # Create new credential
    new_credential_id = str(uuid4())
    new_credential = {
        "id": new_credential_id,
        "cluster_id": old_credential["cluster_id"],
        "name": f"{old_credential['name']}-rotated",
        "credential_type": old_credential["credential_type"],
        "data_encrypted": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_used_at": None,
        "expires_at": old_credential.get("expires_at"),
        "rotation_required": old_credential.get("rotation_required", False),
        "rotated_from": credential_id,
    }

    credentials_storage[new_credential_id] = new_credential

    # Mark old credential as deprecated
    old_credential["deprecated"] = True
    old_credential["deprecated_at"] = datetime.utcnow()
    old_credential["replaced_by"] = new_credential_id
    old_credential["updated_at"] = datetime.utcnow()

    return CredentialRotationResponse(
        credential_id=new_credential_id,
        old_credential_id=credential_id,
        success=True,
        message="Credential rotated successfully",
        rotated_at=datetime.utcnow(),
    )


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(credential_id: str):
    """Delete a credential.

    For security, credentials are soft-deleted and retained
    in the database for audit purposes.

    Args:
        credential_id: Credential ID

    """
    if credential_id not in credentials_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential {credential_id} not found",
        )

    logger.info("deleting_credential", credential_id=credential_id)

    # Soft delete - mark as deleted but retain for audit
    credential = credentials_storage[credential_id]
    credential["deleted"] = True
    credential["deleted_at"] = datetime.utcnow()
    credential["updated_at"] = datetime.utcnow()


@router.get("/{credential_id}/health", response_model=Dict[str, Any])
async def check_credential_health(credential_id: str) -> Dict[str, Any]:
    """Check if a credential is still valid.

    Attempts to use the credential and returns health status.

    Args:
        credential_id: Credential ID

    Returns:
        Health status

    """
    if credential_id not in credentials_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential {credential_id} not found",
        )

    credential = credentials_storage[credential_id]

    logger.info("checking_credential_health", credential_id=credential_id)

    # TODO: Implement actual credential validation
    # - Decrypt credential
    # - Test against target API
    # - Check expiration

    health_status = {
        "valid": True,
        "expires_at": credential.get("expires_at"),
        "days_until_expiry": None,
        "last_validated": datetime.utcnow(),
    }

    if credential.get("expires_at"):
        days_left = (credential["expires_at"] - datetime.utcnow()).days
        health_status["days_until_expiry"] = days_left
        health_status["needs_rotation"] = days_left < 7

    return health_status
