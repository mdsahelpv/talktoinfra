"""Verify all enterprise modules work correctly."""
import asyncio
import os
os.environ["TALKTOINFRA_AUTH_JWT_SECRET"] = "test-secret-for-verification"

import pytest
from src.auth.jwt import create_token, decode_token
from src.auth.rbac import has_permission, Permission, resolve_permissions
from src.safety.guardrails import guardrail_engine
from src.policy.engine import policy_engine, PolicyDecision
from src.storage.repository import AuditRepository
from src.storage.database import create_db_and_tables


class TestAuthJWT:
    def test_create_and_decode_token(self):
        token = create_token("user1", ["admin"], "org1")
        payload = decode_token(token)
        assert payload["sub"] == "user1"
        assert payload["roles"] == ["admin"]
        assert payload["org_id"] == "org1"

    def test_token_expiry(self):
        from datetime import timedelta
        import jwt
        token = create_token("user1", ["viewer"], expires_delta=timedelta(seconds=-1))
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token)


class TestRBAC:
    def test_admin_has_all(self):
        assert has_permission(["admin"], Permission.ADMIN) is True
        assert has_permission(["admin"], Permission.SESSION_DELETE) is True
        assert has_permission(["admin"], Permission.APPROVE_DESTRUCTIVE) is True

    def test_viewer_limited(self):
        assert has_permission(["viewer"], Permission.ADMIN) is False
        assert has_permission(["viewer"], Permission.TOOL_EXECUTE) is False
        assert has_permission(["viewer"], Permission.APPROVE_MUTATE) is False

    def test_operator_can_approve_mutate_not_destructive(self):
        assert has_permission(["operator"], Permission.APPROVE_MUTATE) is True
        assert has_permission(["operator"], Permission.APPROVE_DESTRUCTIVE) is False

    def test_auditor_can_read_export(self):
        assert has_permission(["auditor"], Permission.AUDIT_READ) is True
        assert has_permission(["auditor"], Permission.AUDIT_EXPORT) is True
        assert has_permission(["auditor"], Permission.TOOL_EXECUTE) is False

    def test_resolve_permissions(self):
        perms = resolve_permissions(["viewer"])
        assert Permission.SESSION_READ in perms
        assert Permission.TOOL_READ in perms
        assert Permission.TOOL_EXECUTE not in perms


class TestGuardrails:
    def test_detects_ssh_key(self):
        result = guardrail_engine.check_tool_args("test", {"key": "-----BEGIN RSA PRIVATE KEY-----"})
        assert result.allowed is True
        assert len(result.flags) > 0

    def test_detects_ip(self):
        result = guardrail_engine.check_tool_args("test", {"host": "10.0.0.1"})
        assert "ip_address" in result.flags
        assert result.redacted_args["host"] == "<REDACTED>"

    def test_clean_data_passes(self):
        result = guardrail_engine.check_tool_args("test", {"namespace": "default", "name": "web-1"})
        assert result.allowed is True
        assert result.flags == []

    def test_detects_aws_key(self):
        result = guardrail_engine.check_tool_args("test", {"key": "AKIAIOSFODNN7EXAMPLE"})
        assert "aws_access_key" in result.flags

    def test_blocks_leaky_llm_output(self):
        result = guardrail_engine.check_llm_output("The API key is AKIAIOSFODNN7EXAMPLE")
        assert result.allowed is False
        assert "aws_access_key" in result.flags

    def test_redacts_nested(self):
        result = guardrail_engine.check_tool_args("test", {"db": {"host": "10.0.0.1", "port": 5432}})
        assert result.redacted_args["db"]["host"] == "<REDACTED>"


class TestPolicyEngine:
    def test_read_auto_approved(self):
        r = policy_engine.evaluate({"tier": "read", "tool_name": "k8s_get_pods", "tool_args": {}})
        assert r.decision == PolicyDecision.ALLOW

    def test_mutate_requires_approval(self):
        r = policy_engine.evaluate({"tier": "mutate", "tool_name": "k8s_restart_deployment", "tool_args": {}})
        assert r.decision == PolicyDecision.REQUIRE_APPROVAL

    def test_destructive_requires_approval(self):
        r = policy_engine.evaluate({"tier": "destructive", "tool_name": "k8s_delete_namespace", "tool_args": {"namespace": "staging"}})
        assert r.decision == PolicyDecision.REQUIRE_APPROVAL

    def test_blocks_kube_system_delete(self):
        r = policy_engine.evaluate({"tier": "destructive", "tool_name": "k8s_delete_namespace", "tool_args": {"namespace": "kube-system"}})
        assert r.decision == PolicyDecision.DENY

    def test_blocks_prod_termination(self):
        r = policy_engine.evaluate({"tier": "destructive", "tool_name": "aws_terminate_instance", "tool_args": {"instance_id": "i-prod-123"}})
        assert r.decision == PolicyDecision.DENY


@pytest.mark.asyncio
class TestAuditRepository:
    @pytest.fixture(autouse=True)
    async def setup_db(self):
        await create_db_and_tables()

    async def test_log_and_verify_chain(self):
        repo = AuditRepository()
        e1 = await repo.log({
            "user_id": "u1", "org_id": "org1",
            "action": "k8s_get_pods", "tool_name": "k8s_get_pods",
            "tier": "read", "approved": True, "status": "completed",
        })
        assert e1

        e2 = await repo.log({
            "user_id": "u1", "org_id": "org1",
            "action": "k8s_delete_namespace", "tool_name": "k8s_delete_namespace",
            "tool_args": {"namespace": "staging"},
            "tier": "destructive", "approved": False, "status": "denied",
        })
        assert e2

        violations = await repo.verify_chain()
        assert violations == [], f"Chain violations: {violations}"

    async def test_list_by_org(self):
        repo = AuditRepository()
        entries = await repo.list(org_id="org1")
        assert len(entries) >= 2

    async def test_update_approval(self):
        repo = AuditRepository()
        e = await repo.log({
            "user_id": "u1", "org_id": "org1",
            "action": "test_action", "tool_name": "test",
            "tier": "mutate", "approved": False, "status": "pending",
        })
        updated = await repo.update_approval(e, "admin-user", "Approved after review")
        assert updated is True
