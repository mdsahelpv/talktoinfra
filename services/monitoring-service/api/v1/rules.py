"""Alert Rules API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models_alerts import (
    AlertRule,
    ConditionType,
    EscalationPolicy,
    NotificationChannel,
)
from app.schemas import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
    EscalationPolicyCreate,
    EscalationPolicyResponse,
    EscalationPolicyUpdate,
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
)

router = APIRouter(prefix="/rules", tags=["Alert Rules"])


# ============ Alert Rules ============

@router.get("", response_model=List[AlertRuleResponse])
async def list_rules(
    enabled: Optional[bool] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db_session),
) -> List[AlertRuleResponse]:
    """List all alert rules.

    Args:
        enabled: Filter by enabled status
        severity: Filter by severity
        db: Database session

    Returns:
        List of alert rules
    """
    query = db.query(AlertRule)

    if enabled is not None:
        query = query.filter(AlertRule.enabled == enabled)

    if severity:
        query = query.filter(AlertRule.severity == severity)

    rules = query.order_by(AlertRule.created_at.desc()).all()
    return [AlertRuleResponse.from_orm(r) for r in rules]


@router.get("/{rule_id}", response_model=AlertRuleResponse)
async def get_rule(
    rule_id: int,
    db: Session = Depends(get_db_session),
) -> AlertRuleResponse:
    """Get a specific alert rule by ID.

    Args:
        rule_id: Rule ID
        db: Database session

    Returns:
        Alert rule details

    Raises:
        HTTPException: If rule not found
    """
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()

    if not rule:
        raise HTTPException(
            status_code=404, detail=f"Rule {rule_id} not found")

    return AlertRuleResponse.from_orm(rule)


@router.post("", response_model=AlertRuleResponse)
async def create_rule(
    rule_data: AlertRuleCreate,
    db: Session = Depends(get_db_session),
) -> AlertRuleResponse:
    """Create a new alert rule.

    Args:
        rule_data: Alert rule data
        db: Database session

    Returns:
        Created alert rule
    """
    import json

    rule = AlertRule(
        name=rule_data.name,
        description=rule_data.description,
        enabled=rule_data.enabled,
        condition_type=rule_data.condition_type,
        metric_name=rule_data.metric_name,
        comparison_operator=rule_data.comparison_operator,
        threshold_value=rule_data.threshold_value,
        duration_seconds=rule_data.duration_seconds,
        severity=rule_data.severity,
        labels=json.dumps(rule_data.labels),
        annotations=json.dumps(rule_data.annotations),
        evaluation_interval_seconds=rule_data.evaluation_interval_seconds,
        group_name=rule_data.group_name,
        notify_channels=json.dumps(rule_data.notify_channels),
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return AlertRuleResponse.from_orm(rule)


@router.patch("/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(
    rule_id: int,
    rule_data: AlertRuleUpdate,
    db: Session = Depends(get_db_session),
) -> AlertRuleResponse:
    """Update an existing alert rule.

    Args:
        rule_id: Rule ID
        rule_data: Updated rule data
        db: Database session

    Returns:
        Updated alert rule

    Raises:
        HTTPException: If rule not found
    """
    import json

    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()

    if not rule:
        raise HTTPException(
            status_code=404, detail=f"Rule {rule_id} not found")

    # Update fields
    update_data = rule_data.dict(exclude_unset=True)

    for field, value in update_data.items():
        if field in ["labels", "annotations", "notify_channels"]:
            # Convert dict to JSON string
            if value is not None:
                value = json.dumps(value)
        setattr(rule, field, value)

    rule.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(rule)

    return AlertRuleResponse.from_orm(rule)


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Delete an alert rule.

    Args:
        rule_id: Rule ID
        db: Database session

    Returns:
        Confirmation message

    Raises:
        HTTPException: If rule not found
    """
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()

    if not rule:
        raise HTTPException(
            status_code=404, detail=f"Rule {rule_id} not found")

    db.delete(rule)
    db.commit()

    return {"status": "deleted", "rule_id": rule_id}


@router.post("/{rule_id}/enable")
async def enable_rule(
    rule_id: int,
    db: Session = Depends(get_db_session),
) -> AlertRuleResponse:
    """Enable an alert rule.

    Args:
        rule_id: Rule ID
        db: Database session

    Returns:
        Updated alert rule

    Raises:
        HTTPException: If rule not found
    """
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()

    if not rule:
        raise HTTPException(
            status_code=404, detail=f"Rule {rule_id} not found")

    rule.enabled = True
    rule.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(rule)

    return AlertRuleResponse.from_orm(rule)


@router.post("/{rule_id}/disable")
async def disable_rule(
    rule_id: int,
    db: Session = Depends(get_db_session),
) -> AlertRuleResponse:
    """Disable an alert rule.

    Args:
        rule_id: Rule ID
        db: Database session

    Returns:
        Updated alert rule

    Raises:
        HTTPException: If rule not found
    """
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()

    if not rule:
        raise HTTPException(
            status_code=404, detail=f"Rule {rule_id} not found")

    rule.enabled = False
    rule.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(rule)

    return AlertRuleResponse.from_orm(rule)


# ============ Escalation Policies ============

@router.get("/escalation", response_model=List[EscalationPolicyResponse])
async def list_escalation_policies(
    db: Session = Depends(get_db_session),
) -> List[EscalationPolicyResponse]:
    """List all escalation policies.

    Args:
        db: Database session

    Returns:
        List of escalation policies
    """
    policies = db.query(EscalationPolicy).order_by(
        EscalationPolicy.created_at.desc()
    ).all()

    return [EscalationPolicyResponse.from_orm(p) for p in policies]


@router.get("/escalation/{policy_id}", response_model=EscalationPolicyResponse)
async def get_escalation_policy(
    policy_id: int,
    db: Session = Depends(get_db_session),
) -> EscalationPolicyResponse:
    """Get a specific escalation policy.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Escalation policy details
    """
    policy = db.query(EscalationPolicy).filter(
        EscalationPolicy.id == policy_id
    ).first()

    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"Escalation policy {policy_id} not found"
        )

    return EscalationPolicyResponse.from_orm(policy)


@router.post("/escalation", response_model=EscalationPolicyResponse)
async def create_escalation_policy(
    policy_data: EscalationPolicyCreate,
    db: Session = Depends(get_db_session),
) -> EscalationPolicyResponse:
    """Create a new escalation policy.

    Args:
        policy_data: Escalation policy data
        db: Database session

    Returns:
        Created escalation policy
    """
    import json

    policy = EscalationPolicy(
        name=policy_data.name,
        description=policy_data.description,
        escalation_levels=json.dumps([
            level.dict() for level in policy_data.escalation_levels
        ]),
        repeat_interval_seconds=policy_data.repeat_interval_seconds,
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return EscalationPolicyResponse.from_orm(policy)


@router.patch("/escalation/{policy_id}", response_model=EscalationPolicyResponse)
async def update_escalation_policy(
    policy_id: int,
    policy_data: EscalationPolicyUpdate,
    db: Session = Depends(get_db_session),
) -> EscalationPolicyResponse:
    """Update an escalation policy.

    Args:
        policy_id: Policy ID
        policy_data: Updated policy data
        db: Database session

    Returns:
        Updated escalation policy
    """
    import json

    policy = db.query(EscalationPolicy).filter(
        EscalationPolicy.id == policy_id
    ).first()

    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"Escalation policy {policy_id} not found"
        )

    update_data = policy_data.dict(exclude_unset=True)

    for field, value in update_data.items():
        if field == "escalation_levels" and value is not None:
            value = json.dumps([level.dict() for level in value])
        setattr(policy, field, value)

    policy.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(policy)

    return EscalationPolicyResponse.from_orm(policy)


@router.delete("/escalation/{policy_id}")
async def delete_escalation_policy(
    policy_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Delete an escalation policy.

    Args:
        policy_id: Policy ID
        db: Database session

    Returns:
        Confirmation message
    """
    policy = db.query(EscalationPolicy).filter(
        EscalationPolicy.id == policy_id
    ).first()

    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"Escalation policy {policy_id} not found"
        )

    db.delete(policy)
    db.commit()

    return {"status": "deleted", "policy_id": policy_id}


# ============ Notification Channels ============

@router.get("/channels", response_model=List[NotificationChannelResponse])
async def list_notification_channels(
    channel_type: Optional[str] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db_session),
) -> List[NotificationChannelResponse]:
    """List all notification channels.

    Args:
        channel_type: Filter by channel type
        enabled: Filter by enabled status
        db: Database session

    Returns:
        List of notification channels
    """
    query = db.query(NotificationChannel)

    if channel_type:
        query = query.filter(NotificationChannel.channel_type == channel_type)

    if enabled is not None:
        query = query.filter(NotificationChannel.enabled == enabled)

    channels = query.order_by(NotificationChannel.created_at.desc()).all()

    return [NotificationChannelResponse.from_orm(c) for c in channels]


@router.get("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def get_notification_channel(
    channel_id: int,
    db: Session = Depends(get_db_session),
) -> NotificationChannelResponse:
    """Get a specific notification channel.

    Args:
        channel_id: Channel ID
        db: Database session

    Returns:
        Notification channel details
    """
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=404,
            detail=f"Notification channel {channel_id} not found"
        )

    return NotificationChannelResponse.from_orm(channel)


@router.post("/channels", response_model=NotificationChannelResponse)
async def create_notification_channel(
    channel_data: NotificationChannelCreate,
    db: Session = Depends(get_db_session),
) -> NotificationChannelResponse:
    """Create a new notification channel.

    Args:
        channel_data: Channel data
        db: Database session

    Returns:
        Created notification channel
    """
    import json

    channel = NotificationChannel(
        name=channel_data.name,
        channel_type=channel_data.channel_type,
        config=json.dumps(channel_data.config),
        enabled=channel_data.enabled,
    )

    db.add(channel)
    db.commit()
    db.refresh(channel)

    return NotificationChannelResponse.from_orm(channel)


@router.patch("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def update_notification_channel(
    channel_id: int,
    channel_data: NotificationChannelUpdate,
    db: Session = Depends(get_db_session),
) -> NotificationChannelResponse:
    """Update a notification channel.

    Args:
        channel_id: Channel ID
        channel_data: Updated channel data
        db: Database session

    Returns:
        Updated notification channel
    """
    import json

    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=404,
            detail=f"Notification channel {channel_id} not found"
        )

    update_data = channel_data.dict(exclude_unset=True)

    for field, value in update_data.items():
        if field == "config" and value is not None:
            value = json.dumps(value)
        setattr(channel, field, value)

    channel.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(channel)

    return NotificationChannelResponse.from_orm(channel)


@router.delete("/channels/{channel_id}")
async def delete_notification_channel(
    channel_id: int,
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Delete a notification channel.

    Args:
        channel_id: Channel ID
        db: Database session

    Returns:
        Confirmation message
    """
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=404,
            detail=f"Notification channel {channel_id} not found"
        )

    db.delete(channel)
    db.commit()

    return {"status": "deleted", "channel_id": channel_id}


@router.post("/channels/{channel_id}/enable")
async def enable_notification_channel(
    channel_id: int,
    db: Session = Depends(get_db_session),
) -> NotificationChannelResponse:
    """Enable a notification channel.

    Args:
        channel_id: Channel ID
        db: Database session

    Returns:
        Updated channel
    """
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=404,
            detail=f"Notification channel {channel_id} not found"
        )

    channel.enabled = True
    channel.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(channel)

    return NotificationChannelResponse.from_orm(channel)


@router.post("/channels/{channel_id}/disable")
async def disable_notification_channel(
    channel_id: int,
    db: Session = Depends(get_db_session),
) -> NotificationChannelResponse:
    """Disable a notification channel.

    Args:
        channel_id: Channel ID
        db: Database session

    Returns:
        Updated channel
    """
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=404,
            detail=f"Notification channel {channel_id} not found"
        )

    channel.enabled = False
    channel.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(channel)

    return NotificationChannelResponse.from_orm(channel)
