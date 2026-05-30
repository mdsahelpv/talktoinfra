"""Tests for the PII/secret redactor."""

from src.safety.redactor import Redactor


def test_redact_api_key():
    r = Redactor()
    text = 'api_key = "sk-1234567890abcdef1234567890abcdef"'
    result = r.redact(text)
    assert "***REDACTED***" in result
    assert "sk-1234567890abcdef1234567890abcdef" not in result


def test_redact_ip():
    r = Redactor()
    text = "Server IP is 192.168.1.100"
    result = r.redact(text)
    assert "***IP_REDACTED***" in result
    assert "192.168.1.100" not in result


def test_redact_password():
    r = Redactor()
    text = 'password: "supersecret123!"'
    result = r.redact(text)
    assert "***REDACTED***" in result


def test_redact_no_false_positive():
    r = Redactor()
    text = "This is normal text with no secrets"
    result = r.redact(text)
    assert result == text
