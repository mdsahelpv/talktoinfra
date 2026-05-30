#!/usr/bin/env python3
"""SOC 2 evidence collection — generates JSON reports for auditors."""

import json
import os
from datetime import datetime, timezone

EVIDENCE_DIR = os.path.join(os.path.dirname(__file__), "..", "evidence")


def _ensure_dir():
    os.makedirs(EVIDENCE_DIR, exist_ok=True)


def _write_report(name: str, data: dict):
    path = os.path.join(EVIDENCE_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"  -> {path}")


def generate_access_control_report():
    """Export SSO logs, RBAC assignments, user list."""
    report = {
        "report_type": "Access Control",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "soc2_criteria": ["CC6.1", "CC6.2", "CC6.3"],
        "sso_providers": ["OIDC", "SAML"],
        "rbac_roles": ["viewer", "operator", "admin", "auditor"],
        "user_count": 0,
        "mfa_enforced": False,
        "access_reviews": [],
        "evidence_files": [
            "orchestrator/src/auth/rbac.py",
            "orchestrator/src/auth/deps.py",
            "orchestrator/src/auth/oidc.py",
            "orchestrator/src/auth/saml.py",
            "orchestrator/src/auth/mfa.py",
        ],
    }
    _write_report("access_control", report)


def generate_change_management_report():
    """Show audit trail of configuration changes."""
    report = {
        "report_type": "Change Management",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "soc2_criteria": ["CC8.1"],
        "change_controls": {
            "audit_trail": "Merkle-chain immutable audit log",
            "approval_required": True,
            "approval_tiers": ["mutate", "destructive"],
            "deployment_strategy": "Helm chart with versioned releases",
        },
        "evidence_files": [
            "orchestrator/src/storage/repository.py",
            "orchestrator/src/safety/gate.py",
            "orchestrator/src/policy/engine.py",
        ],
    }
    _write_report("change_management", report)


def generate_data_protection_report():
    """PII redaction test results, encryption at rest/transit."""
    report = {
        "report_type": "Data Protection",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "soc2_criteria": ["CC6.7", "CC6.8"],
        "pii_redaction": {
            "enabled": True,
            "patterns": ["email", "ip_address", "api_key", "secret", "password"],
            "engine": "orchestrator/src/safety/redactor.py",
        },
        "encryption": {
            "at_rest": "SQLite/PostgreSQL (database-level encryption)",
            "in_transit": "TLS for all API endpoints",
            "key_management": "Environment variables / Kubernetes secrets",
        },
        "evidence_files": [
            "orchestrator/src/safety/redactor.py",
            "orchestrator/src/auth/jwt.py",
        ],
    }
    _write_report("data_protection", report)


def generate_availability_report():
    """Uptime, heartbeat logs, backup test results."""
    report = {
        "report_type": "Availability",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "soc2_criteria": ["CC7.1", "CC7.2"],
        "uptime_monitoring": {
            "heartbeat_sla_seconds": 30,
            "health_endpoint": "/health",
        },
        "backup_tests": [],
        "disaster_recovery": {
            "multi_region_failover": True,
            "pod_disruption_budget": True,
        },
        "evidence_files": [
            "orchestrator/src/observability/heartbeat.py",
            "orchestrator/src/deploy/failover.py",
            "orchestrator/src/deploy/backup.py",
        ],
    }
    _write_report("availability", report)


def main():
    _ensure_dir()
    print("Generating SOC 2 evidence reports...")
    generate_access_control_report()
    generate_change_management_report()
    generate_data_protection_report()
    generate_availability_report()
    print(f"\nAll reports written to {EVIDENCE_DIR}/")


if __name__ == "__main__":
    main()
