"""PII/Secret redaction before sending data to LLM providers."""

import re


class Redactor:
    def __init__(self):
        self._patterns = [
            (re.compile(r'(?i)(api[_-]?key["\']?\s*[:=]\s*["\']?)[A-Za-z0-9_\-]{16,}'), r'\1***REDACTED***'),
            (re.compile(r'(?i)(password["\']?\s*[:=]\s*["\']?)[^"\'\s]{4,}'), r'\1***REDACTED***'),
            (re.compile(r'(?i)(secret["\']?\s*[:=]\s*["\']?)[^"\'\s]{4,}'), r'\1***REDACTED***'),
            (re.compile(r'(?i)(token["\']?\s*[:=]\s*["\']?)[A-Za-z0-9_\-\.]{16,}'), r'\1***REDACTED***'),
            (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '***IP_REDACTED***'),
            (re.compile(r'["\'][A-Za-z0-9+/=]{40,}["\']'), '"***POTENTIAL_KEY***"'),
        ]

    def redact(self, text: str) -> str:
        result = text
        for pattern, replacement in self._patterns:
            result = pattern.sub(replacement, result)
        return result
