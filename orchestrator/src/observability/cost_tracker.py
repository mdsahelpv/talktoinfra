"""Cost tracking — per-session token usage and budget enforcement."""

import logging
from datetime import datetime, timezone

from src.config import settings

logger = logging.getLogger(__name__)


class CostTracker:
    def __init__(self) -> None:
        self._usage: list[dict] = []

    def record_usage(
        self,
        session_id: str,
        user_id: str,
        org_id: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
    ) -> None:
        self._usage.append({
            "session_id": session_id,
            "user_id": user_id,
            "org_id": org_id,
            "provider": provider,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_session_cost(self, session_id: str) -> float:
        return sum(u["cost"] for u in self._usage if u["session_id"] == session_id)

    def get_org_costs(self, org_id: str, since: str = "", until: str = "") -> dict:
        filtered = [u for u in self._usage if u["org_id"] == org_id]
        if since:
            filtered = [u for u in filtered if u["timestamp"] >= since]
        if until:
            filtered = [u for u in filtered if u["timestamp"] <= until]
        total = sum(u["cost"] for u in filtered)
        return {
            "org_id": org_id,
            "total_cost": total,
            "usage_count": len(filtered),
            "by_provider": {
                p: sum(u["cost"] for u in filtered if u["provider"] == p)
                for p in {u["provider"] for u in filtered}
            },
        }

    def check_budget(self, org_id: str) -> dict:
        budget = settings.cost_budget_per_org
        if budget <= 0:
            return {"alert": False, "reason": "No budget configured"}
        total = sum(u["cost"] for u in self._usage if u["org_id"] == org_id)
        ratio = total / budget
        threshold = settings.cost_alert_threshold
        if ratio >= 1.0:
            return {"alert": True, "reason": f"Budget exhausted (${total:.2f} / ${budget:.2f})"}
        if ratio >= threshold:
            return {"alert": True, "reason": f"Budget threshold reached ({ratio:.0%} of ${budget:.2f})"}
        return {"alert": False, "reason": f"{ratio:.0%} of budget used"}
