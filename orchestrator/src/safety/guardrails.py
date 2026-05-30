"""Content-aware guardrails — scans tool arguments and LLM output for sensitive data."""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str = ""
    redacted_args: dict[str, Any] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)


# ── Patterns ────────────────────────────────────────────────────────────

PATTERNS: list[tuple[str, str]] = [
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("aws_secret_key", r"(?i)aws.?secret.?access.?key[=:]\s*\S+"),
    ("github_token", r"ghp_[0-9a-zA-Z]{36}"),
    ("slack_token", r"xox[baprs]-[0-9a-zA-Z]{10,72}"),
    ("ssh_private_key", r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ("jwt_token", r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),
    ("basic_auth", r"Authorization:\s*Basic\s+[A-Za-z0-9+/=]{10,}"),
    ("ip_address", r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"),
    ("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ("credit_card", r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b"),
    ("phone_number", r"\b\+?\d{1,3}[-\s]?\d{1,4}[-\s]?\d{1,4}[-\s]?\d{1,4}\b"),
    ("slack_webhook", r"https://hooks\.slack\.com/services/[A-Za-z0-9/]{20,}"),
    ("google_api_key", r"AIza[0-9A-Za-z_-]{35}"),
    ("stripe_api_key", r"sk_live_[0-9a-zA-Z]{24,}"),
    ("pg_connection", r"postgres(?:ql)?://[^\s]+"),
    ("redis_connection", r"redis://[^\s]+"),
    ("mongo_connection", r"mongodb(?:\+srv)?://[^\s]+"),
]


REDACT_LABEL = "<REDACTED>"


def scan_value(value: str) -> list[str]:
    """Scan a string value for sensitive patterns. Returns list of flags."""
    flags = []
    for name, pattern in PATTERNS:
        if re.search(pattern, value):
            flags.append(name)
    return flags


def scan_dict(data: dict, path: str = "") -> dict[str, list[str]]:
    """Recursively scan a dict for sensitive patterns."""
    results: dict[str, list[str]] = {}
    for key, val in data.items():
        current_path = f"{path}.{key}" if path else key
        if isinstance(val, str):
            flags = scan_value(val)
            if flags:
                results[current_path] = flags
        elif isinstance(val, dict):
            nested = scan_dict(val, current_path)
            results.update(nested)
        elif isinstance(val, list):
            for i, item in enumerate(val):
                if isinstance(item, str):
                    flags = scan_value(item)
                    if flags:
                        results[f"{current_path}[{i}]"] = flags
                elif isinstance(item, dict):
                    nested = scan_dict(item, f"{current_path}[{i}]")
                    results.update(nested)
    return results


def redact_value(value: str) -> str:
    """Redact sensitive patterns from a string."""
    result = value
    for _, pattern in PATTERNS:
        result = re.sub(pattern, REDACT_LABEL, result)
    return result


def redact_dict(data: dict) -> dict:
    """Return a copy of dict with sensitive values redacted."""
    redacted: dict = {}
    for key, val in data.items():
        if isinstance(val, str):
            redacted[key] = redact_value(val)
        elif isinstance(val, dict):
            redacted[key] = redact_dict(val)
        elif isinstance(val, list):
            redacted[key] = [redact_value(v) if isinstance(v, str) else v for v in val]
        else:
            redacted[key] = val
    return redacted


class GuardrailEngine:
    """Content-aware guardrail scanner for tool arguments."""

    def check_tool_args(self, tool_name: str, args: dict) -> GuardrailResult:
        flags = scan_dict(args)
        if flags:
            flagged_paths = [f"{k}: {', '.join(v)}" for k, v in flags.items()]
            redacted = redact_dict(args)
            return GuardrailResult(
                allowed=True,
                reason=f"Sensitive data detected and redacted in: {'; '.join(flagged_paths)}",
                redacted_args=redacted,
                flags=list(set(f for fv in flags.values() for f in fv)),
            )
        return GuardrailResult(allowed=True, reason="No sensitive data detected")

    def check_llm_output(self, text: str) -> GuardrailResult:
        flags = scan_value(text)
        if flags:
            return GuardrailResult(
                allowed=False,
                reason=f"LLM output contains sensitive patterns: {', '.join(flags)}",
                redacted_args={"text": redact_value(text)},
                flags=flags,
            )
        return GuardrailResult(allowed=True, reason="Output clean")


guardrail_engine = GuardrailEngine()
