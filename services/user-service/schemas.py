"""User Service Pydantic Schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Base schemas
class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""

    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """User update schema."""

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[dict] = None


class UserResponse(UserBase):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    is_superuser: bool
    mfa_enabled: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    """User list response schema."""

    total: int
    users: list[UserResponse]


# Authentication schemas
class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


# MFA schemas
class EnableMFARequest(BaseModel):
    """Enable MFA request schema."""

    password: str


class VerifyMFARequest(BaseModel):
    """Verify MFA request schema."""

    code: str = Field(..., min_length=6, max_length=6)


class MFAResponse(BaseModel):
    """MFA response schema."""

    secret: str
    qr_code: str
    message: str


# Team schemas
class TeamBase(BaseModel):
    """Base team schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    """Team creation schema."""

    pass


class TeamUpdate(BaseModel):
    """Team update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    settings: Optional[dict] = None


class TeamResponse(TeamBase):
    """Team response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    avatar_url: Optional[str] = None
    settings: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class TeamListResponse(BaseModel):
    """Team list response schema."""

    total: int
    teams: list[TeamResponse]


class TeamMemberResponse(BaseModel):
    """Team member response schema."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    team_id: UUID
    role: str
    user: UserResponse
    created_at: datetime


# Role schemas
class RoleBase(BaseModel):
    """Base role schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Role creation schema."""

    role_type: str = "user"
    permissions: Optional[dict] = None


class RoleUpdate(BaseModel):
    """Role update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[dict] = None


class RoleResponse(RoleBase):
    """Role response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role_type: str
    permissions: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


# Cluster Access schemas
class ClusterAccessBase(BaseModel):
    """Base cluster access schema."""

    cluster_id: UUID
    permission_level: str = "read"


class ClusterAccessCreate(ClusterAccessBase):
    """Cluster access creation schema."""

    namespace_access: Optional[dict] = None
    label_selector: Optional[dict] = None


class ClusterAccessUpdate(BaseModel):
    """Cluster access update schema."""

    permission_level: Optional[str] = None
    namespace_access: Optional[dict] = None
    label_selector: Optional[dict] = None


class ClusterAccessResponse(ClusterAccessBase):
    """Cluster access response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    namespace_access: Optional[dict] = None
    label_selector: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


# API Key schemas
class ApiKeyBase(BaseModel):
    """Base API key schema."""

    name: str = Field(..., min_length=1, max_length=100)


class ApiKeyCreate(ApiKeyBase):
    """API key creation schema."""

    permissions: Optional[dict] = None
    expires_at: Optional[datetime] = None


class ApiKeyResponse(ApiKeyBase):
    """API key response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    prefix: str
    permissions: Optional[dict] = None
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None


class ApiKeyWithSecret(ApiKeyResponse):
    """API key with secret (only shown once)."""

    api_key: str


# Session schemas
class SessionResponse(BaseModel):
    """Session response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime


# Permission check schemas
class PermissionCheckRequest(BaseModel):
    """Permission check request schema."""

    resource_type: str
    resource_id: str
    action: str


class PermissionCheckResponse(BaseModel):
    """Permission check response schema."""

    allowed: bool
    reason: Optional[str] = None


# Health check
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
