"""
Pydantic schemas for API requests and responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ==================== Scan Schemas ====================


class ScanPortSchema(BaseModel):
    """Port discovered on a host."""

    port: int = Field(..., ge=1, le=65535)
    status: str = Field(..., pattern="^(open|closed|filtered)$")
    service: Optional[str] = None
    service_version: Optional[str] = None
    banner: Optional[str] = None
    protocol: str = Field(default="tcp", pattern="^(tcp|udp)$")


class DiscoveredHostSchema(BaseModel):
    """Host discovered during scan."""

    id: UUID
    ip_address: str
    hostname: Optional[str] = None
    status: str = Field(..., pattern="^(alive|unreachable|filtered)$")
    response_time_ms: Optional[int] = None
    ports: List[ScanPortSchema] = []
    discovered_at: datetime

    class Config:
        from_attributes = True


class ScanJobSchema(BaseModel):
    """Scan job information."""

    id: UUID
    status: str = Field(..., pattern="^(pending|running|completed|failed|cancelled)$")
    scan_type: str = Field(..., pattern="^(fast|detailed|hybrid|python)$")
    progress: int = Field(..., ge=0, le=100)

    ip_range: str
    ports: List[int]

    total_hosts: Optional[int] = None
    scanned_hosts: int
    found_hosts: int

    created_by: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    config: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class ScanJobListSchema(BaseModel):
    """List of scan jobs with pagination."""

    items: List[ScanJobSchema]
    total: int
    page: int
    page_size: int
    pages: int


class ScanStartRequest(BaseModel):
    """Request to start a new scan."""

    ip_range: str = Field(
        ...,
        min_length=7,
        max_length=100,
        description="IP range in CIDR (192.168.1.0/24), range (192.168.1.1-192.168.1.100), or single IP (192.168.1.1) format",
    )
    ports: List[int] = Field(
        ..., min_length=1, max_length=1000, description="Ports to scan"
    )
    scan_type: str = Field(
        default="hybrid",
        pattern="^(fast|detailed|hybrid|python)$",
        description="Scanner type to use",
    )
    timeout: Optional[float] = Field(
        default=None, ge=0.5, le=60.0, description="Timeout per host in seconds"
    )
    concurrent_limit: Optional[int] = Field(
        default=None, ge=10, le=500, description="Max concurrent connections"
    )
    service_detection: bool = Field(
        default=True, description="Enable service detection"
    )
    require_approval: bool = Field(
        default=False, description="Require admin approval before scanning"
    )

    @field_validator("ip_range")
    @classmethod
    def validate_ip_range(cls, v: str) -> str:
        from app.utils.ip_range import validate_ip_range, IPRangeParseError

        try:
            # Validate and normalize the IP range
            # Max 65536 hosts (same as before)
            normalized, _ = validate_ip_range(v, max_size=65536)
            return normalized
        except IPRangeParseError as e:
            raise ValueError(f"Invalid IP range: {e}")

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v: List[int]) -> List[int]:
        if len(v) > 1000:
            raise ValueError("Cannot scan more than 1000 ports at once")
        if any(p < 1 or p > 65535 for p in v):
            raise ValueError("Invalid port number. Must be between 1 and 65535")
        return sorted(set(v))  # Remove duplicates and sort


class ScanStatusResponse(BaseModel):
    """Current status of a scan job."""

    job_id: UUID
    status: str
    progress: int
    total_hosts: Optional[int]
    scanned_hosts: int
    found_hosts: int
    current_phase: Optional[str] = None
    estimated_time_remaining: Optional[int] = None  # seconds
    message: Optional[str] = None


class ScanResultsResponse(BaseModel):
    """Results of a scan job."""

    job_id: UUID
    status: str
    total_hosts: int
    found_hosts: int
    hosts: List[DiscoveredHostSchema]


# ==================== Host Management Schemas ====================


class ManagedHostSchema(BaseModel):
    """Managed host information."""

    id: UUID
    name: str
    ip_address: str
    ports: List[int]
    services: List[str]
    status: str = Field(..., pattern="^(online|offline|unknown|degraded)$")
    last_checked_at: Optional[datetime] = None
    first_discovered_at: datetime
    discovered_by_job_id: Optional[UUID] = None
    added_at: datetime
    added_by: str
    notes: Optional[str] = None
    host_metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class ManagedHostListSchema(BaseModel):
    """List of managed hosts with pagination."""

    items: List[ManagedHostSchema]
    total: int
    page: int
    page_size: int
    pages: int


class AddHostRequest(BaseModel):
    """Request to add a discovered host to managed hosts."""

    discovered_host_id: UUID
    name: Optional[str] = None
    notes: Optional[str] = None


class CreateHostRequest(BaseModel):
    """Request to manually create a managed host."""

    name: str = Field(..., min_length=1, max_length=255)
    ip_address: str = Field(..., pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    ports: List[int] = Field(default=[])
    services: List[str] = Field(default=[])
    notes: Optional[str] = None

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v: List[int]) -> List[int]:
        if any(p < 1 or p > 65535 for p in v):
            raise ValueError("Invalid port number")
        return sorted(set(v))


class UpdateHostRequest(BaseModel):
    """Request to update a managed host."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ==================== Health Check Schemas ====================


class HealthCheckSchema(BaseModel):
    """Health check record."""

    id: UUID
    status: str
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    checked_at: datetime

    class Config:
        from_attributes = True


class HostHealthHistorySchema(BaseModel):
    """Health history for a managed host."""

    host_id: UUID
    checks: List[HealthCheckSchema]
    uptime_percentage: float
    total_checks: int
    last_24h_status_changes: int


class HostStatusUpdate(BaseModel):
    """Status update for a host."""

    host_id: UUID
    previous_status: str
    new_status: str
    changed_at: datetime
    response_time_ms: Optional[int] = None


# ==================== Discovery Status Schemas ====================


class DiscoveryStatusSchema(BaseModel):
    """Overall discovery service status."""

    total_scans: int
    active_scans: int
    completed_scans_24h: int
    total_managed_hosts: int
    online_hosts: int
    offline_hosts: int
    health_check_enabled: bool
    last_health_check: Optional[datetime] = None


class PortPresetSchema(BaseModel):
    """Port preset configuration."""

    name: str
    description: str
    ports: List[int]


class PortPresetsListSchema(BaseModel):
    """List of available port presets."""

    presets: List[PortPresetSchema]


# ==================== Scanner Configuration Schemas ====================


class ScannerInfoSchema(BaseModel):
    """Information about available scanners."""

    name: str
    description: str
    available: bool
    requires_root: bool
    recommended_for: str
    average_speed: str  # e.g., "1000 hosts/sec"


class ScannersListSchema(BaseModel):
    """List of available scanners."""

    scanners: List[ScannerInfoSchema]
    recommended: str


# ==================== Error Schemas ====================


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
