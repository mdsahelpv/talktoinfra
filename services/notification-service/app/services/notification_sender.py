"""Notification Sender Service."""

import json
import smtplib
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiohttp
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models import (
    Notification,
    NotificationChannel,
    NotificationLog,
    NotificationPreference,
    NotificationPriority,
    NotificationStatus,
    NotificationTemplate,
    WebhookConfig,
)

settings = get_settings()


class NotificationSender:
    """Service for sending notifications through various channels."""

    def __init__(self, db: AsyncSession):
        """Initialize notification sender."""
        self.db = db

    async def send_notification(
        self,
        user_id: uuid.UUID,
        title: str,
        message: str,
        channel: NotificationChannel,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        metadata: Optional[dict] = None,
        action_url: Optional[str] = None,
    ) -> Notification:
        """Send a notification to a user."""
        # Create notification record
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            channel=channel,
            priority=priority,
            metadata=metadata,
            action_url=action_url,
            status=NotificationStatus.PENDING,
        )

        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        # Get user preferences
        result = await self.db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id
            )
        )
        preferences = result.scalar_one_or_none()

        # Check if channel is enabled
        if not self._is_channel_enabled(channel, preferences):
            notification.status = NotificationStatus.FAILED
            notification.error_message = f"Channel {channel.value} is disabled for user"
            await self.db.commit()
            return notification

        # Get contact info
        contact = self._get_contact(channel, preferences)

        # Send based on channel
        try:
            if channel == NotificationChannel.EMAIL:
                await self._send_email(contact, title, message, notification)
            elif channel == NotificationChannel.SLACK:
                await self._send_slack(contact, title, message, notification)
            elif channel == NotificationChannel.TEAMS:
                await self._send_teams(contact, title, message, notification)
            elif channel == NotificationChannel.PAGERDUTY:
                await self._send_pagerduty(contact, title, message, priority, notification)
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook(contact, title, message, notification)
            elif channel == NotificationChannel.IN_APP:
                await self._send_in_app(notification)
            else:
                raise ValueError(f"Unknown channel: {channel}")
        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            await self.db.commit()

        return notification

    def _is_channel_enabled(
        self, channel: NotificationChannel, preferences: Optional[NotificationPreference]
    ) -> bool:
        """Check if channel is enabled in preferences."""
        if not preferences:
            return True  # Default to enabled

        channel_map = {
            NotificationChannel.EMAIL: preferences.email_enabled,
            NotificationChannel.SLACK: preferences.slack_enabled,
            NotificationChannel.TEAMS: preferences.teams_enabled,
            NotificationChannel.PAGERDUTY: preferences.pagerduty_enabled,
            NotificationChannel.IN_APP: preferences.in_app_enabled,
        }

        return channel_map.get(channel, True)

    def _get_contact(
        self, channel: NotificationChannel, preferences: Optional[NotificationPreference]
    ) -> Optional[str]:
        """Get contact info for channel."""
        if not preferences:
            return None

        contact_map = {
            NotificationChannel.EMAIL: preferences.email,
            NotificationChannel.SLACK: preferences.slack_user_id,
            NotificationChannel.TEAMS: preferences.teams_user_id,
            NotificationChannel.PAGERDUTY: preferences.pagerduty_user_id,
        }

        return contact_map.get(channel)

    async def _send_email(
        self,
        to_email: Optional[str],
        title: str,
        message: str,
        notification: Notification,
    ) -> None:
        """Send email notification."""
        if not to_email or not settings.smtp_host:
            raise ValueError("Email not configured")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = title
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to_email

        # Plain text part
        text_part = MIMEText(message, "plain")
        msg.attach(text_part)

        # HTML part (simple conversion)
        html_part = MIMEText(
            f"<html><body><h1>{title}</h1><p>{message}</p></body></html>", "html"
        )
        msg.attach(html_part)

        # Send email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_user and settings.smtp_password:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, to_email, msg.as_string())

        # Log success
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        await self._log_delivery(notification.id, NotificationChannel.EMAIL, "sent", 200)

    async def _send_slack(
        self,
        slack_user_id: Optional[str],
        title: str,
        message: str,
        notification: Notification,
    ) -> None:
        """Send Slack notification."""
        if not slack_user_id or not settings.slack_bot_token:
            raise ValueError("Slack not configured")

        # Priority emoji
        priority_emoji = {
            NotificationPriority.LOW: "ℹ️",
            NotificationPriority.MEDIUM: "⚠️",
            NotificationPriority.HIGH: "🔴",
            NotificationPriority.CRITICAL: "🚨",
        }

        payload = {
            "channel": slack_user_id,
            "text": f"{priority_emoji.get(notification.priority, '')} {title}",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": title},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message},
                },
            ],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://slack.com/api/chat.postMessage",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.slack_bot_token}",
                    "Content-Type": "application/json",
                },
            ) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    raise ValueError(f"Slack API error: {data}")

        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        await self._log_delivery(notification.id, NotificationChannel.SLACK, "sent", 200)

    async def _send_teams(
        self,
        teams_user_id: Optional[str],
        title: str,
        message: str,
        notification: Notification,
    ) -> None:
        """Send Microsoft Teams notification."""
        if not settings.teams_webhook_url:
            raise ValueError("Teams webhook not configured")

        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": title,
            "themeColor": self._get_priority_color(notification.priority),
            "title": title,
            "text": message,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                settings.teams_webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=settings.webhook_timeout),
            ) as resp:
                if resp.status >= 400:
                    raise ValueError(f"Teams webhook error: {resp.status}")

        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        await self._log_delivery(notification.id, NotificationChannel.TEAMS, "sent", 200)

    async def _send_pagerduty(
        self,
        pagerduty_user_id: Optional[str],
        title: str,
        message: str,
        priority: NotificationPriority,
        notification: Notification,
    ) -> None:
        """Send PagerDuty notification."""
        if not settings.pagerduty_api_key or not settings.pagerduty_service_id:
            raise ValueError("PagerDuty not configured")

        # Map priority to PagerDuty urgency
        urgency = "high" if priority in [NotificationPriority.HIGH, NotificationPriority.CRITICAL] else "low"

        payload = {
            "routing_key": settings.pagerduty_service_id,
            "event_action": "trigger",
            "payload": {
                "summary": title,
                "severity": priority.value,
                "source": "TalkAI",
                "custom_details": {"message": message},
            },
            "urgency": urgency,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                headers={
                    "Authorization": f"Token token={settings.pagerduty_api_key}",
                    "Content-Type": "application/json",
                },
            ) as resp:
                data = await resp.json()
                if resp.status >= 400 or "dedup_key" not in data:
                    raise ValueError(f"PagerDuty error: {data}")

        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        await self._log_delivery(notification.id, NotificationChannel.PAGERDUTY, "sent", 202)

    async def _send_webhook(
        self,
        webhook_url: Optional[str],
        title: str,
        message: str,
        notification: Notification,
    ) -> None:
        """Send webhook notification."""
        if not webhook_url:
            raise ValueError("Webhook URL not provided")

        payload = {
            "title": title,
            "message": message,
            "priority": notification.priority.value,
            "metadata": notification.metadata,
            "timestamp": datetime.utcnow().isoformat(),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=settings.webhook_timeout),
            ) as resp:
                if resp.status >= 400:
                    raise ValueError(f"Webhook error: {resp.status}")

        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        await self._log_delivery(notification.id, NotificationChannel.WEBHOOK, "sent", resp.status)

    async def _send_in_app(self, notification: Notification) -> None:
        """Mark in-app notification as sent."""
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()
        await self.db.commit()

    async def _log_delivery(
        self,
        notification_id: uuid.UUID,
        channel: NotificationChannel,
        status: str,
        status_code: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log notification delivery."""
        log = NotificationLog(
            notification_id=notification_id,
            channel=channel,
            status=status,
            status_code=status_code,
            error_message=error,
        )
        self.db.add(log)
        await self.db.commit()

    def _get_priority_color(self, priority: NotificationPriority) -> str:
        """Get color for priority."""
        colors = {
            NotificationPriority.LOW: "0078D4",
            NotificationPriority.MEDIUM: "FFB900",
            NotificationPriority.HIGH: "D83B01",
            NotificationPriority.CRITICAL: "E81123",
        }
        return colors.get(priority, "0078D4")


class TemplateService:
    """Service for managing notification templates."""

    def __init__(self, db: AsyncSession):
        """Initialize template service."""
        self.db = db

    async def render_template(
        self,
        template_name: str,
        variables: dict,
    ) -> dict:
        """Render a notification template with variables."""
        result = await self.db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.name == template_name
            )
        )
        template = result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Template not found: {template_name}")

        # Simple variable substitution
        subject = template.subject or ""
        body = template.body_template or ""
        html = template.html_template or ""

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
            html = html.replace(placeholder, str(value))

        return {
            "subject": subject,
            "body": body,
            "html": html,
        }
