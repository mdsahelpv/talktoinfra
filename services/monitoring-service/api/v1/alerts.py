"""Alert API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models_alerts import Alert, AlertHistory, AlertRule, AlertSeverity, AlertStatus
from app.schemas import (
    AlertAcknowledge,
    AlertFilter,
    AlertListResponse,
    AlertResolve,
    AlertResponse,
)
from app.services.alerting import get_alerting_engine

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[List[AlertStatus]] = Query(None),
    severity: Optional[List[AlertSeverity]] = Query(None),
    rule_id: Optional[int] = None,
    group_name: Optional[str] = None,
    fingerprint: Optional[str] = None,
    starts_after: Optional[datetime] = None,
    starts_before: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db_session),
) -> AlertListResponse:
    """List alerts with filtering and pagination.

    Args:
        status: Filter by alert status
        severity: Filter by severity
        rule_id: Filter by rule ID
        group_name: Filter by group name
        fingerprint: Filter by fingerprint
        starts_after: Filter by start time (after)
        starts_before: Filter by start time (before)
        page: Page number
        page_size: Items per page
        db: Database session

    Returns:
        Paginated list of alerts
    """
    query = db.query(Alert)

    # Apply filters
    if status:
        query = query.filter(Alert.status.in_(status))

    if severity:
        query = query.filter(Alert.severity.in_(severity))

    if rule_id:
        query = query.filter(Alert.rule_id == rule_id)

    if group_name:
        query = query.filter(Alert.group_name == group_name)

    if fingerprint:
        query = query.filter(Alert.fingerprint == fingerprint)

    if starts_after:
        query = query.filter(Alert.starts_at >= starts_after)

    if starts_before:
        query = query.filter(Alert.starts_at <= starts_before)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    alerts = query.order_by(Alert.starts_at.desc()).offset(
        offset).limit(page_size).all()

    # Convert to response
    alert_responses = []
    for alert in alerts:
        rule = db.query(AlertRule).filter(
            AlertRule.id == alert.rule_id).first()
        alert_responses.append(
            AlertResponse(
                id=alert.id,
                fingerprint=alert.fingerprint,
                rule_id=alert.rule_id,
                title=alert.title,
                description=alert.description,
                severity=alert.severity or AlertSeverity.WARNING,
                status=alert.status or AlertStatus.ACTIVE,
                labels=alert.labels_dict,
                annotations=alert.annotations_dict,
                current_value=alert.current_value,
                threshold_value=alert.threshold_value,
                starts_at=alert.starts_at,
                ends_at=alert.ends_at,
                acknowledged_at=alert.acknowledged_at,
                resolved_at=alert.resolved_at,
                acknowledged_by=alert.acknowledged_by,
                resolved_by=alert.resolved_by,
                acknowledgment_notes=alert.acknowledgment_notes,
                fire_count=alert.fire_count,
                group_name=alert.group_name,
                root_cause_alert_id=alert.root_cause_alert_id,
                created_at=alert.created_at,
                updated_at=alert.updated_at,
                rule=AlertResponse.from_orm(rule).dict() if rule else None,
            )
        )

    return AlertListResponse(
        alerts=alert_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts(
    severity: Optional[List[AlertSeverity]] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db_session),
) -> List[AlertResponse]:
    """Get currently active (unresolved) alerts.

    Args:
        severity: Filter by severity
        limit: Maximum number of alerts to return
        db: Database session

    Returns:
        List of active alerts
    """
    query = db.query(Alert).filter(
        Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED])
    )

    if severity:
        query = query.filter(Alert.severity.in_(severity))

    alerts = query.order_by(
        Alert.severity.desc(),
        Alert.starts_at.desc()
    ).limit(limit).all()

    return [AlertResponse.from_orm(alert) for alert in alerts]


@router.get("/statistics")
async def get_alert_statistics(
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """Get alert statistics for dashboard.

    Args:
        db: Database session

    Returns:
        Dictionary with alert statistics
    """
    # Total counts by status
    total_alerts = db.query(Alert).count()
    active_alerts = db.query(Alert).filter(
        Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED])
    ).count()
    acknowledged_alerts = db.query(Alert).filter(
        Alert.status == AlertStatus.ACKNOWLEDGED
    ).count()
    resolved_alerts = db.query(Alert).filter(
        Alert.status == AlertStatus.RESOLVED
    ).count()

    # Counts by severity
    severity_counts = {}
    for severity in AlertSeverity:
        count = db.query(Alert).filter(Alert.severity == severity).count()
        severity_counts[severity.value] = count

    # Counts by status
    status_counts = {}
    for status in AlertStatus:
        count = db.query(Alert).filter(Alert.status == status).count()
        status_counts[status.value] = count

    # Counts by group
    group_counts = {}
    groups = db.query(Alert.group_name).distinct().all()
    for (group_name,) in groups:
        if group_name:
            count = db.query(Alert).filter(
                Alert.group_name == group_name).count()
            group_counts[group_name] = count

    return {
        "total_alerts": total_alerts,
        "active_alerts": active_alerts,
        "acknowledged_alerts": acknowledged_alerts,
        "resolved_alerts": resolved_alerts,
        "by_severity": severity_counts,
        "by_status": status_counts,
        "by_group": group_counts,
    }


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db_session),
) -> AlertResponse:
    """Get a specific alert by ID.

    Args:
        alert_id: Alert ID
        db: Database session

    Returns:
        Alert details

    Raises:
        HTTPException: If alert not found
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(
            status_code=404, detail=f"Alert {alert_id} not found")

    return AlertResponse.from_orm(alert)


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    acknowledgment: AlertAcknowledge,
    db: Session = Depends(get_db_session),
) -> AlertResponse:
    """Acknowledge an alert.

    Args:
        alert_id: Alert ID
        acknowledgment: Acknowledgment details
        db: Database session

    Returns:
        Updated alert

    Raises:
        HTTPException: If alert not found or cannot be acknowledged
    """
    alerting_engine = get_alerting_engine()

    try:
        alert = await alerting_engine.acknowledge_alert(alert_id, acknowledgment)
        db.commit()
        return AlertResponse.from_orm(alert)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    resolution: AlertResolve,
    db: Session = Depends(get_db_session),
) -> AlertResponse:
    """Resolve an alert.

    Args:
        alert_id: Alert ID
        resolution: Resolution details
        db: Database session

    Returns:
        Updated alert

    Raises:
        HTTPException: If alert not found or cannot be resolved
    """
    alerting_engine = get_alerting_engine()

    try:
        alert = await alerting_engine.resolve_alert(alert_id, resolution)
        db.commit()
        return AlertResponse.from_orm(alert)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}/history")
async def get_alert_history(
    alert_id: int,
    db: Session = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    """Get alert lifecycle history.

    Args:
        alert_id: Alert ID
        db: Database session

    Returns:
        List of history entries

    Raises:
        HTTPException: If alert not found
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(
            status_code=404, detail=f"Alert {alert_id} not found")

    history = db.query(AlertHistory).filter(
        AlertHistory.alert_id == alert_id
    ).order_by(AlertHistory.created_at.desc()).all()

    return [
        {
            "id": h.id,
            "alert_id": h.alert_id,
            "previous_status": h.previous_status,
            "new_status": h.new_status,
            "changed_by": h.changed_by,
            "change_reason": h.change_reason,
            "created_at": h.created_at,
        }
        for h in history
    ]


@router.post("/{alert_id}/silence")
async def silence_alert(
    alert_id: int,
    duration_minutes: int = Query(60, ge=1, le=1440),
    reason: Optional[str] = None,
    db: Session = Depends(get_db_session),
) -> AlertResponse:
    """Silence (suppress) an alert for a duration.

    Args:
        alert_id: Alert ID
        duration_minutes: How long to silence the alert
        reason: Reason for silencing
        db: Database session

    Returns:
        Updated alert

    Raises:
        HTTPException: If alert not found
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(
            status_code=404, detail=f"Alert {alert_id} not found")

    # Create history entry
    history = AlertHistory(
        alert_id=alert_id,
        previous_status=alert.status.value if alert.status else None,
        new_status=AlertStatus.SUPPRESSED.value,
        change_reason=f"Silenced for {duration_minutes} minutes: {reason}",
    )

    # Update alert
    alert.status = AlertStatus.SUPPRESSED
    alert.updated_at = datetime.utcnow()

    db.add(history)
    db.commit()

    return AlertResponse.from_orm(alert)
