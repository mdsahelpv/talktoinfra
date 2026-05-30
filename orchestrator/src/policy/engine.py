"""Policy enforcement engine — wraps OPA/Rego evaluation with built-in defaults."""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class PolicyResult:
    decision: PolicyDecision
    reason: str = ""
    constraints: dict[str, Any] = field(default_factory=dict)


# ── Built-in policy rules (Rego-compatible format) ──────────────────────

BUILTIN_POLICIES: dict[str, str] = {
    "default_deny": """
package talktoinfra.policy

default allow = false
""",
    "read_auto_approve": """
package talktoinfra.policy

allow {
    input.tier == "read"
    input.tool_name != ""
}
""",
    "mutate_requires_approval": """
package talktoinfra.policy

allow = false {
    input.tier == "mutate"
}

require_approval {
    input.tier == "mutate"
}
""",
    "destructive_requires_approval": """
package talktoinfra.policy

allow = false {
    input.tier == "destructive"
}

require_approval {
    input.tier == "destructive"
}
""",
    "no_delete_kube_system": """
package talktoinfra.policy

deny {
    input.tool_name == "k8s_delete_namespace"
    input.tool_args.namespace == "kube-system"
}
""",
    "no_terminate_production": """
package talktoinfra.policy

deny {
    input.tool_name == "aws_terminate_instance"
    regex.match(".*prod.*", input.tool_args.instance_id)
}
""",
}


class PolicyEngine:
    """Simple built-in policy engine. In production, delegates to OPA sidecar."""

    def __init__(self) -> None:
        self._policies: dict[str, str] = dict(BUILTIN_POLICIES)

    def evaluate(self, input_data: dict) -> PolicyResult:
        tier = input_data.get("tier", "read")
        tool_name = input_data.get("tool_name", "")
        tool_args = input_data.get("tool_args", {}) or {}
        user_roles = input_data.get("user_roles", ["viewer"])

        # 1. Blocklist checks
        if tool_name == "k8s_delete_namespace" and tool_args.get("namespace") == "kube-system":
            return PolicyResult(PolicyDecision.DENY, "kube-system namespace deletion is blocked by policy")

        if tool_name == "aws_terminate_instance" and re.search(r"prod", tool_args.get("instance_id", ""), re.I):
            return PolicyResult(PolicyDecision.DENY, "Terminating production instances is blocked by policy")

        # 2. Tier-based enforcement
        if tier == "destructive":
            return PolicyResult(PolicyDecision.REQUIRE_APPROVAL, "Destructive actions require fresh approval")

        if tier == "mutate":
            return PolicyResult(PolicyDecision.REQUIRE_APPROVAL, "Mutate actions require session approval")

        if tier == "read":
            return PolicyResult(PolicyDecision.ALLOW, "Read actions auto-approved")

        return PolicyResult(PolicyDecision.DENY, f"Unknown tier: {tier}")

    def add_policy(self, name: str, rego_source: str) -> None:
        self._policies[name] = rego_source


policy_engine = PolicyEngine()
