"""
Audit Service

Provides comprehensive audit logging and compliance capabilities.
Features immutable logs with hashing, query capabilities, and compliance reporting.
"""

import hashlib
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import Settings, get_settings
from models import (
    AuditLogEntry,
    AuditLogRequest,
    AuditQueryRequest,
    AuditQueryResponse,
    AuditExportRequest,
    AuditExportResponse,
    ComplianceReport,
    ComplianceReportRequest,
    LogIntegrityReport,
)
from log_store import LogStore
from integrity import IntegrityVerifier

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Service components
log_store: Optional[LogStore] = None
integrity_verifier: Optional[IntegrityVerifier] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global log_store, integrity_verifier

    settings = get_settings()

    logger.info("audit_service_initializing", port=settings.service_port)

    # Initialize components
    log_store = LogStore(
        storage_path=settings.log_storage_path,
        retention_days=settings.log_retention_days,
    )
    integrity_verifier = IntegrityVerifier(
        hash_algorithm=settings.hash_algorithm,
    )

    logger.info("audit_service_ready")

    yield

    # Cleanup
    logger.info("audit_service_shutting_down")


app = FastAPI(
    title="AI Infrastructure Operations - Audit Service",
    description="Audit logging and compliance tracking with immutable logs",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests with context."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    try:
        logger.info("request_started")
        response = await call_next(request)
        logger.info("request_completed", status_code=response.status_code)
        return response
    finally:
        structlog.contextvars.clear_contextvars()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "audit-service",
        "timestamp": time.time(),
        "components": {
            "log_store": "healthy" if log_store else "unhealthy",
            "integrity_verifier": "healthy" if integrity_verifier else "unhealthy",
        },
    }


@app.post("/audit/log")
async def log_audit_event(request: Request, log_entry: AuditLogRequest):
    """Log an audit event with integrity hashing."""
    try:
        entry_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        # Get client info
        client_host = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Create full audit entry
        audit_entry = AuditLogEntry(
            id=entry_id,
            timestamp=timestamp,
            user_id=log_entry.user_id,
            action=log_entry.action,
            resource_type=log_entry.resource_type,
            resource_id=log_entry.resource_id,
            service=log_entry.service,
            details=log_entry.details,
            ip_address=client_host,
            user_agent=user_agent,
            request_id=request.state.request_id,
        )

        # Calculate hash for integrity
        entry_hash = integrity_verifier.calculate_hash(audit_entry)
        audit_entry.hash = entry_hash
        audit_entry.previous_hash = await log_store.get_last_hash()

        # Store the entry
        await log_store.store(audit_entry)

        logger.info(
            "audit_event_logged",
            entry_id=entry_id,
            action=log_entry.action,
            user_id=log_entry.user_id,
        )

        return {
            "success": True,
            "entry_id": entry_id,
            "hash": entry_hash,
            "timestamp": timestamp.isoformat(),
        }

    except Exception as e:
        logger.error("audit_log_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log audit event: {str(e)}",
        )


@app.get("/audit/query", response_model=AuditQueryResponse)
async def query_audit_logs(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    service: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Query audit logs with filters."""
    try:
        logger.info(
            "audit_query",
            user_id=user_id,
            action=action,
            start_time=start_time,
            end_time=end_time,
        )

        # Build query filters
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if action:
            filters["action"] = action
        if resource_type:
            filters["resource_type"] = resource_type
        if resource_id:
            filters["resource_id"] = resource_id
        if service:
            filters["service"] = service

        # Query logs
        results = await log_store.query(
            start_time=start_time,
            end_time=end_time,
            filters=filters,
            limit=limit,
            offset=offset,
        )

        # Get total count
        total = await log_store.count(
            start_time=start_time,
            end_time=end_time,
            filters=filters,
        )

        logger.info(
            "audit_query_completed",
            results_count=len(results),
            total=total,
        )

        return AuditQueryResponse(
            entries=results,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error("audit_query_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query audit logs: {str(e)}",
        )


@app.post("/audit/query", response_model=AuditQueryResponse)
async def query_audit_logs_post(query: AuditQueryRequest):
    """Query audit logs with POST (for complex queries)."""
    return await query_audit_logs(
        start_time=query.start_time,
        end_time=query.end_time,
        user_id=query.user_id,
        action=query.action,
        resource_type=query.resource_type,
        resource_id=query.resource_id,
        service=query.service,
        limit=query.limit,
        offset=query.offset,
    )


@app.get("/audit/export")
async def export_audit_logs(
    start_time: datetime,
    end_time: datetime,
    format: str = "json",
    user_id: Optional[str] = None,
    action: Optional[str] = None,
):
    """Export audit logs in various formats."""
    try:
        logger.info(
            "audit_export",
            format=format,
            start_time=start_time,
            end_time=end_time,
        )

        # Query logs
        logs = await log_store.query(
            start_time=start_time,
            end_time=end_time,
            filters={"user_id": user_id, "action": action},
            limit=10000,
        )

        # Export based on format
        if format == "json":
            content = json.dumps(
                [log.model_dump() for log in logs],
                indent=2,
                default=str,
            )
            media_type = "application/json"
            filename = f"audit_export_{start_time.date()}_{end_time.date()}.json"

        elif format == "csv":
            content = convert_to_csv(logs)
            media_type = "text/csv"
            filename = f"audit_export_{start_time.date()}_{end_time.date()}.csv"

        elif format == "ndjson":
            lines = [json.dumps(log.model_dump(), default=str) for log in logs]
            content = "\n".join(lines)
            media_type = "application/x-ndjson"
            filename = f"audit_export_{start_time.date()}_{end_time.date()}.ndjson"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}",
            )

        logger.info(
            "audit_export_completed",
            format=format,
            entries_count=len(logs),
        )

        return StreamingResponse(
            iter([content]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("audit_export_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export audit logs: {str(e)}",
        )


@app.get("/audit/integrity/verify")
async def verify_log_integrity(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """Verify the integrity of audit logs using hash chain."""
    try:
        logger.info("integrity_verification_started")

        # Get logs to verify
        logs = await log_store.query(
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        verification_results = []
        tampered_count = 0

        for i, log in enumerate(logs):
            # Verify hash
            is_valid = integrity_verifier.verify_hash(log)

            # Verify chain (if not first log)
            chain_valid = True
            if i > 0:
                expected_previous_hash = logs[i - 1].hash
                if log.previous_hash != expected_previous_hash:
                    chain_valid = False
                    tampered_count += 1

            verification_results.append(
                {
                    "entry_id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "hash_valid": is_valid,
                    "chain_valid": chain_valid,
                }
            )

        total_logs = len(logs)
        verified = tampered_count == 0

        logger.info(
            "integrity_verification_completed",
            total_logs=total_logs,
            tampered_count=tampered_count,
            verified=verified,
        )

        return LogIntegrityReport(
            verified=verified,
            total_logs=total_logs,
            tampered_entries=tampered_count,
            verification_date=datetime.utcnow(),
            details=verification_results[:100],  # Limit details in response
        )

    except Exception as e:
        logger.error("integrity_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify integrity: {str(e)}",
        )


@app.get("/audit/entry/{entry_id}", response_model=AuditLogEntry)
async def get_audit_entry(entry_id: str):
    """Get a specific audit entry by ID."""
    entry = await log_store.get_by_id(entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit entry not found",
        )
    return entry


@app.post("/compliance/report", response_model=ComplianceReport)
async def generate_compliance_report(request: ComplianceReportRequest):
    """Generate a compliance report for a time period."""
    try:
        logger.info(
            "compliance_report_generation",
            report_type=request.report_type,
            start_time=request.start_time,
            end_time=request.end_time,
        )

        # Query relevant logs
        logs = await log_store.query(
            start_time=request.start_time,
            end_time=request.end_time,
            limit=10000,
        )

        # Calculate metrics
        total_actions = len(logs)
        unique_users = len(set(log.user_id for log in logs))

        # Action breakdown
        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1

        # Service breakdown
        service_counts = {}
        for log in logs:
            service_counts[log.service] = service_counts.get(log.service, 0) + 1

        # High-risk actions
        high_risk_actions = [
            log
            for log in logs
            if log.action in ["delete", "terminate", "rollback", "execute"]
        ]

        # Failed actions (if failure info is in details)
        failed_actions = [
            log
            for log in logs
            if log.details.get("status") == "failed"
            or log.details.get("success") is False
        ]

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type=request.report_type,
            generated_at=datetime.utcnow(),
            period_start=request.start_time,
            period_end=request.end_time,
            total_actions=total_actions,
            unique_users=unique_users,
            action_breakdown=action_counts,
            service_breakdown=service_counts,
            high_risk_actions=len(high_risk_actions),
            failed_actions=len(failed_actions),
            compliance_status="compliant"
            if len(failed_actions) == 0
            else "review_required",
            summary=f"Period from {request.start_time.date()} to {request.end_time.date()}: "
            f"{total_actions} actions by {unique_users} users. "
            f"{len(high_risk_actions)} high-risk actions, "
            f"{len(failed_actions)} failures.",
        )

        logger.info(
            "compliance_report_generated",
            report_id=report.report_id,
            total_actions=total_actions,
        )

        return report

    except Exception as e:
        logger.error("compliance_report_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@app.get("/audit/stats")
async def get_audit_stats(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """Get statistics about audit logs."""
    try:
        # Use default time range if not provided
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(days=7)

        total_logs = await log_store.count(
            start_time=start_time,
            end_time=end_time,
        )

        # Get unique counts
        logs = await log_store.query(
            start_time=start_time,
            end_time=end_time,
            limit=10000,
        )

        unique_users = len(set(log.user_id for log in logs))
        unique_services = len(set(log.service for log in logs))

        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
            },
            "total_logs": total_logs,
            "unique_users": unique_users,
            "unique_services": unique_services,
            "action_counts": action_counts,
        }

    except Exception as e:
        logger.error("audit_stats_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}",
        )


def convert_to_csv(logs: List[AuditLogEntry]) -> str:
    """Convert audit logs to CSV format."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "id",
            "timestamp",
            "user_id",
            "action",
            "resource_type",
            "resource_id",
            "service",
            "ip_address",
            "hash",
        ]
    )

    # Data
    for log in logs:
        writer.writerow(
            [
                log.id,
                log.timestamp.isoformat(),
                log.user_id,
                log.action,
                log.resource_type,
                log.resource_id,
                log.service,
                log.ip_address,
                log.hash,
            ]
        )

    return output.getvalue()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)
