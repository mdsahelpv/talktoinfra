"""Notification API Routes."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from models import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationPriority,
    NotificationStatus,
)
from app.services.notification_sender import NotificationSender

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# Request/Response schemas
class SendNotificationRequest(BaseModel):
    """Send notification request."""

    user_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=500)
    message: str
    channel: NotificationChannel = NotificationChannel.IN_APP
    priority: NotificationPriority = NotificationPriority.MEDIUM
    metadata: Optional[dict] = None
    action_url: Optional[str] = None


class NotificationResponse(BaseModel):
    """Notification response."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    channel: NotificationChannel
    priority: NotificationPriority
    status: NotificationStatus
    action_url: Optional[str] = None
    created_at: str
    sent_at: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class PreferenceUpdateRequest(BaseModel):
    """Update notification preferences."""

    email_enabled: Optional[bool] = None
    slack_enabled: Optional[bool] = None
    teams_enabled: Optional[bool] = None
    pagerduty_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    alerts_enabled: Optional[bool] = None
    approvals_enabled: Optional[bool] = None
    workflow_enabled: Optional[bool] = None
    digest_enabled: Optional[bool] = None
    email: Optional[str] = None
    slack_user_id: Optional[str] = None
    teams_user_id: Optional[str] = None
    pagerduty_user_id: Optional[str] = None
    digest_frequency: Optional[str] = None


class PreferenceResponse(BaseModel):
    """Notification preference response."""

    user_id: uuid.UUID
    email_enabled: bool
    slack_enabled: bool
    teams_enabled: bool
    pagerduty_enabled: bool
    in_app_enabled: bool
    alerts_enabled: bool
    approvals_enabled: bool
    workflow_enabled: bool
    digest_enabled: bool
    email: Optional[str] = None
    slack_user_id: Optional[str] = None
    teams_user_id: Optional[str] = None
    pagerduty_user_id: Optional[str] = None
    digest_frequency: str


# Endpoints
@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a notification to a user."""
    sender = NotificationSender(db)

    notification = await sender.send_notification(
        user_id=request.user_id,
        title=request.title,
        message=request.message,
        channel=request.channel,
        priority=request.priority,
        metadata=request.metadata,
        action_url=request.action_url,
    )

    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        title=notification.title,
        message=notification.message,
        channel=notification.channel,
        priority=notification.priority,
        status=notification.status,
        action_url=notification.action_url,
        created_at=notification.created_at.isoformat(),
        sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
        error_message=notification.error_message,
    )


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    user_id: Optional[uuid.UUID] = None,
    status_filter: Optional[NotificationStatus] = Query(None, alias="status"),
    channel_filter: Optional[NotificationChannel] = Query(None, alias="channel"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List notifications."""
    query = select(Notification).order_by(Notification.created_at.desc())

    if user_id:
        query = query.where(Notification.user_id == user_id)
    if status_filter:
        query = query.where(Notification.status == status_filter)
    if channel_filter:
        query = query.where(Notification.channel == channel_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)

    # Get paginated results
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        NotificationResponse(
            id=n.id,
            user_id=n.user_id,
            title=n.title,
            message=n.message,
            channel=n.channel,
            priority=n.priority,
            status=n.status,
            action_url=n.action_url,
            created_at=n.created_at.isoformat(),
            sent_at=n.sent_at.isoformat() if n.sent_at else None,
            error_message=n.error_message,
        )
        for n in notifications
    ]


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a notification by ID."""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        title=notification.title,
        message=notification.message,
        channel=notification.channel,
        priority=notification.priority,
        status=notification.status,
        action_url=notification.action_url,
        created_at=notification.created_at.isoformat(),
        sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
        error_message=notification.error_message,
    )


# Preferences endpoints
@router.get("/preferences/me", response_model=PreferenceResponse)
async def get_my_preferences(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get current user's notification preferences."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Return defaults
        return PreferenceResponse(
            user_id=user_id,
            email_enabled=True,
            slack_enabled=False,
            teams_enabled=False,
            pagerduty_enabled=False,
            in_app_enabled=True,
            alerts_enabled=True,
            approvals_enabled=True,
            workflow_enabled=True,
            digest_enabled=False,
            digest_frequency="daily",
        )

    return PreferenceResponse(
        user_id=prefs.user_id,
        email_enabled=prefs.email_enabled,
        slack_enabled=prefs.slack_enabled,
        teams_enabled=prefs.teams_enabled,
        pagerduty_enabled=prefs.pagerduty_enabled,
        in_app_enabled=prefs.in_app_enabled,
        alerts_enabled=prefs.alerts_enabled,
        approvals_enabled=prefs.approvals_enabled,
        workflow_enabled=prefs.workflow_enabled,
        digest_enabled=prefs.digest_enabled,
        email=prefs.email,
        slack_user_id=prefs.slack_user_id,
        teams_user_id=prefs.teams_user_id,
        pagerduty_user_id=prefs.pagerduty_user_id,
        digest_frequency=prefs.digest_frequency,
    )


@router.put("/preferences/me", response_model=PreferenceResponse)
async def update_my_preferences(
    user_id: uuid.UUID,
    prefs: PreferenceUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update current user's notification preferences."""
    result = await db.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id
        )
    )
    preference = result.scalar_one_or_none()

    if not preference:
        # Create new preferences
        preference = NotificationPreference(user_id=user_id)
        db.add(preference)

    # Update fields
    if prefs.email_enabled is not None:
        preference.email_enabled = prefs.email_enabled
    if prefs.slack_enabled is not None:
        preference.slack_enabled = prefs.slack_enabled
    if prefs.teams_enabled is not None:
        preference.teams_enabled = prefs.teams_enabled
    if prefs.pagerduty_enabled is not None:
        preference.pagerduty_enabled = prefs.pagerduty_enabled
    if prefs.in_app_enabled is not None:
        preference.in_app_enabled = prefs.in_app_enabled
    if prefs.alerts_enabled is not None:
        preference.alerts_enabled = prefs.alerts_enabled
    if prefs.approvals_enabled is not None:
        preference.approvals_enabled = prefs.approvals_enabled
    if prefs.workflow_enabled is not None:
        preference.workflow_enabled = prefs.workflow_enabled
    if prefs.digest_enabled is not None:
        preference.digest_enabled = prefs.digest_enabled
    if prefs.email is not None:
        preference.email = prefs.email
    if prefs.slack_user_id is not None:
        preference.slack_user_id = prefs.slack_user_id
    if prefs.teams_user_id is not None:
        preference.teams_user_id = prefs.teams_user_id
    if prefs.pagerduty_user_id is not None:
        preference.pagerduty_user_id = prefs.pagerduty_user_id
    if prefs.digest_frequency is not None:
        preference.digest_frequency = prefs.digest_frequency

    await db.commit()
    await db.refresh(preference)

    return PreferenceResponse(
        user_id=preference.user_id,
        email_enabled=preference.email_enabled,
        slack_enabled=preference.slack_enabled,
        teams_enabled=preference.teams_enabled,
        pagerduty_enabled=preference.pagerduty_enabled,
        in_app_enabled=preference.in_app_enabled,
        alerts_enabled=preference.alerts_enabled,
        approvals_enabled=preference.approvals_enabled,
        workflow_enabled=preference.workflow_enabled,
        digest_enabled=preference.digest_enabled,
        email=preference.email,
        slack_user_id=preference.slack_user_id,
        teams_user_id=preference.teams_user_id,
        pagerduty_user_id=preference.pagerduty_user_id,
        digest_frequency=preference.digest_frequency,
    )
