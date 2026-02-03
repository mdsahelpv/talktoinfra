"""
Pydantic models for Audit Service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    """Audit log entry with integrity hashing."""

    id: str = Field(..., description="Unique entry identifier")
    timestamp: datetime = Field(..., description="Event timestamp")
    user_id: str = Field(..., description="User who performed the action")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    service: str = Field(..., description="Service that logged the event")
    details: Dict[str, Any] = Field(default={}, description="Additional details")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    hash: Optional[str] = Field(None, description="Entry hash for integrity")
    previous_hash: Optional[str] = Field(None, description="Previous entry hash")


class AuditLogRequest(BaseModel):
    """Request to log an audit event."""

    user_id: str = Field(..., description="User who performed the action")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    service: str = Field(..., description="Service logging the event")
    details: Dict[str, Any] = Field(default={}, description="Additional details")


class AuditQueryRequest(BaseModel):
    """Request to query audit logs."""

    start_time: Optional[datetime] = Field(None, description="Start of time range")
    end_time: Optional[datetime] = Field(None, description="End of time range")
    user_id: Optional[str] = Field(None, description="Filter by user")
    action: Optional[str] = Field(None, description="Filter by action")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    service: Optional[str] = Field(None, description="Filter by service")
    limit: int = Field(default=100, ge=1, le=10000, description="Max results")
    offset: int = Field(default=0, ge=0, description="Result offset")


class AuditQueryResponse(BaseModel):
    """Response from audit query."""

    entries: List[AuditLogEntry] = Field(default=[], description="Log entries")
    total: int = Field(..., description="Total matching entries")
    limit: int = Field(..., description="Query limit")
    offset: int = Field(..., description="Query offset")


class AuditExportRequest(BaseModel):
    """Request to export audit logs."""

    start_time: datetime = Field(..., description="Export start time")
    end_time: datetime = Field(..., description="Export end time")
    format: str = Field(default="json", description="Export format (json, csv, ndjson)")
    filters: Dict[str, Any] = Field(default={}, description="Export filters")


class AuditExportResponse(BaseModel):
    """Response from audit export."""

    export_id: str = Field(..., description="Export job ID")
    status: str = Field(..., description="Export status")
    download_url: Optional[str] = Field(None, description="Download URL when ready")
    entries_count: int = Field(..., description="Number of entries exported")
    format: str = Field(..., description="Export format")
    expires_at: Optional[datetime] = Field(None, description="Export expiration")


class ComplianceReportType(str, Enum):
    """Types of compliance reports."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    AUDIT = "audit"
    CUSTOM = "custom"


class ComplianceReportRequest(BaseModel):
    """Request to generate compliance report."""

    report_type: ComplianceReportType = Field(..., description="Report type")
    start_time: datetime = Field(..., description="Report period start")
    end_time: datetime = Field(..., description="Report period end")
    filters: Dict[str, Any] = Field(default={}, description="Report filters")


class ComplianceReport(BaseModel):
    """Compliance report."""

    report_id: str = Field(..., description="Report unique identifier")
    report_type: ComplianceReportType = Field(..., description="Report type")
    generated_at: datetime = Field(..., description="Report generation time")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")
    total_actions: int = Field(..., description="Total actions logged")
    unique_users: int = Field(..., description="Unique users")
    action_breakdown: Dict[str, int] = Field(default={}, description="Actions by type")
    service_breakdown: Dict[str, int] = Field(
        default={}, description="Actions by service"
    )
    high_risk_actions: int = Field(..., description="Number of high-risk actions")
    failed_actions: int = Field(..., description="Number of failed actions")
    compliance_status: str = Field(..., description="Overall compliance status")
    summary: str = Field(..., description="Report summary")


class LogIntegrityReport(BaseModel):
    """Log integrity verification report."""

    verified: bool = Field(..., description="Whether all logs passed verification")
    total_logs: int = Field(..., description="Total logs checked")
    tampered_entries: int = Field(..., description="Number of tampered entries")
    verification_date: datetime = Field(..., description="When verification was run")
    details: List[Dict[str, Any]] = Field(default=[], description="Per-entry details")


class RetentionPolicy(BaseModel):
    """Log retention policy."""

    policy_id: str = Field(..., description="Policy identifier")
    retention_days: int = Field(..., description="Days to retain logs")
    archive_enabled: bool = Field(default=True, description="Enable archiving")
    archive_location: Optional[str] = Field(
        None, description="Archive storage location"
    )
    auto_purge: bool = Field(default=False, description="Auto-purge after retention")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ArchiveJob(BaseModel):
    """Log archive job."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    start_time: Optional[datetime] = Field(None, description="Archive start time")
    end_time: Optional[datetime] = Field(None, description="Archive end time")
    entries_archived: int = Field(default=0, description="Number of entries archived")
    archive_location: Optional[str] = Field(None, description="Archive location")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="Completion time")
