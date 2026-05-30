"""Approval flow integration — routes approval requests to configured backends."""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from src.config import settings

logger = logging.getLogger(__name__)

_pending_approvals: dict[str, dict] = {}


class ApprovalBackend(ABC):
    @abstractmethod
    async def request_approval(self, approval_id: str, action: str, parameters: dict, tier: str, user_id: str) -> bool:
        ...


@dataclass
class WebhookApprovalBackend(ApprovalBackend):
    url: str

    async def request_approval(self, approval_id: str, action: str, parameters: dict, tier: str, user_id: str) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.url, json={
                    "approval_id": approval_id,
                    "action": action,
                    "parameters": parameters,
                    "tier": tier,
                    "user_id": user_id,
                }, timeout=10)
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.error("Webhook approval request failed: %s", exc)
            return False


@dataclass
class SlackApprovalBackend(ApprovalBackend):
    webhook_url: str = ""
    channel: str = ""

    async def request_approval(self, approval_id: str, action: str, parameters: dict, tier: str, user_id: str) -> bool:
        try:
            import httpx
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*Approval Required* — `{action}`"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"Tier: `{tier}` | User: `{user_id}`"}},
                {"type": "actions", "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, "value": f"approve:{approval_id}", "style": "primary"},
                    {"type": "button", "text": {"type": "plain_text", "text": "Deny"}, "value": f"deny:{approval_id}", "style": "danger"},
                ]},
            ]
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.webhook_url, json={"channel": self.channel, "blocks": blocks}, timeout=10)
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.error("Slack approval request failed: %s", exc)
            return False


@dataclass
class EmailApprovalBackend(ApprovalBackend):
    smtp_host: str = ""
    smtp_port: int = 587
    from_addr: str = ""

    async def request_approval(self, approval_id: str, action: str, parameters: dict, tier: str, user_id: str) -> bool:
        logger.info("Email approval backend would send email to %s for action %s (id=%s)", user_id, action, approval_id)
        return True


class ApprovalRouter:
    def __init__(self) -> None:
        self._backends: dict[str, ApprovalBackend] = {}
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        backend_type = settings.approval_backend
        if backend_type == "slack" and settings.approval_slack_webhook_url:
            self._backends["default"] = SlackApprovalBackend(
                webhook_url=settings.approval_slack_webhook_url,
                channel=settings.approval_slack_channel,
            )
        elif backend_type == "email" and settings.approval_email_smtp_host:
            self._backends["default"] = EmailApprovalBackend(
                smtp_host=settings.approval_email_smtp_host,
                from_addr=settings.approval_email_from,
            )
        else:
            self._backends["default"] = WebhookApprovalBackend(url="http://localhost:8000/api/v1/approvals/callback")

    def register_backend(self, name: str, backend: ApprovalBackend) -> None:
        self._backends[name] = backend

    async def route_approval(self, action_tier: str, action: str, parameters: dict, user_id: str) -> str:
        approval_id = str(uuid4())
        backend = self._backends.get("default")
        if backend:
            await backend.request_approval(approval_id, action, parameters, action_tier, user_id)

        _pending_approvals[approval_id] = {
            "action": action,
            "parameters": parameters,
            "tier": action_tier,
            "user_id": user_id,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return approval_id

    def get_pending(self, approval_id: str) -> dict | None:
        return _pending_approvals.get(approval_id)

    def resolve(self, approval_id: str, approved: bool) -> bool:
        pending = _pending_approvals.get(approval_id)
        if not pending:
            return False
        pending["status"] = "approved" if approved else "denied"
        return True


approval_router = ApprovalRouter()
