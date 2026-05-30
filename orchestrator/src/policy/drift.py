"""Policy drift detection — compares current policies against a known baseline."""

import hashlib
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PolicyDriftDetector:
    def __init__(self) -> None:
        self._baseline: dict[str, str] = {}

    def record_baseline(self, policies: dict[str, str]) -> None:
        self._baseline = {}
        for name, source in policies.items():
            self._baseline[name] = hashlib.sha256(source.encode()).hexdigest()
        logger.info("Policy baseline recorded with %d policies", len(policies))

    def check_drift(self, current_policies: dict[str, str]) -> list[dict]:
        drifted = []
        for name, source in current_policies.items():
            current_hash = hashlib.sha256(source.encode()).hexdigest()
            baseline_hash = self._baseline.get(name)
            if baseline_hash is None:
                drifted.append({
                    "policy": name,
                    "type": "new",
                    "detail": "Policy added since baseline was recorded",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            elif current_hash != baseline_hash:
                drifted.append({
                    "policy": name,
                    "type": "modified",
                    "detail": "Policy content changed since baseline",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        for name in self._baseline:
            if name not in current_policies:
                drifted.append({
                    "policy": name,
                    "type": "removed",
                    "detail": "Policy removed since baseline was recorded",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        return drifted

    def get_drift_report(self, current_policies: dict[str, str]) -> str:
        drifted = self.check_drift(current_policies)
        if not drifted:
            return "No policy drift detected. All policies match baseline."
        lines = [f"Policy Drift Report ({len(drifted)} change(s)):", "=" * 50]
        for d in drifted:
            lines.append(f"  [{d['type'].upper()}] {d['policy']}: {d['detail']}")
        return "\n".join(lines)
