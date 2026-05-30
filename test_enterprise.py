"""Verify all enterprise modules work correctly."""
import asyncio
import sys
import os

# Add both the project root and the orchestrator src path
_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_root, "orchestrator", "src"))
# Also try inserting the full path directly
_osp = os.path.normpath(os.path.join(_root, "orchestrator", "src"))
if _osp not in sys.path:
    sys.path.insert(0, _osp)

# Must set a non-default secret for signing to work
os.environ["TALKTOINFRA_AUTH_JWT_SECRET"] = "test-secret-for-verification"

from src.auth.jwt import create_token, decode_token
from src.auth.rbac import has_permission, Permission, resolve_permissions
from src.safety.guardrails import guardrail_engine, scan_value
from src.policy.engine import policy_engine, PolicyDecision
from src.storage.repository import AuditRepository

print("=" * 60)
print("ENTERPRISE MODULE VERIFICATION")
print("=" * 60)

# 1. JWT
print("\n--- JWT ---")
token = create_token("user1", ["admin"], "org1")
payload = decode_token(token)
assert payload["sub"] == "user1"
assert payload["roles"] == ["admin"]
assert payload["org_id"] == "org1"
print(f"  create + decode OK: sub={payload['sub']} roles={payload['roles']}")

# 2. RBAC
print("\n--- RBAC ---")
assert has_permission(["admin"], Permission.ADMIN) == True
assert has_permission(["viewer"], Permission.ADMIN) == False
assert has_permission(["operator"], Permission.APPROVE_MUTATE) == True
assert has_permission(["operator"], Permission.APPROVE_DESTRUCTIVE) == False
assert has_permission(["auditor"], Permission.AUDIT_EXPORT) == True
assert has_permission(["viewer"], Permission.SESSION_READ) == True
assert has_permission(["viewer"], Permission.TOOL_EXECUTE) == False
print("  All RBAC assertions passed")
print(f"  viewer permissions: {sorted(p.value for p in resolve_permissions(['viewer']))}")
print(f"  operator permissions: {sorted(p.value for p in resolve_permissions(['operator']))}")

# 3. Guardrails
print("\n--- Guardrails ---")
result = guardrail_engine.check_tool_args("test", {"password": "my_secret_123", "host": "10.0.0.1"})
assert result.allowed == True
assert "ip_address" in result.flags
assert result.redacted_args["host"] == "<REDACTED>"
print(f"  Sensitive data detected: {result.flags}")
print(f"  Redacted args: {result.redacted_args}")

# Check clean data passes
result2 = guardrail_engine.check_tool_args("test", {"namespace": "default", "pod_name": "web-1"})
assert result2.allowed == True
assert result2.flags == []
print(f"  Clean data: no flags ({result2.flags})")

# Test LLM output guardrails
result3 = guardrail_engine.check_llm_output("The API key is AKIAIOSFODNN7EXAMPLE")
assert result3.allowed == False
assert "aws_access_key" in result3.flags
print(f"  LLM output blocked: {result3.flags}")

# 4. Policy Engine
print("\n--- Policy Engine ---")
r = policy_engine.evaluate({"tier": "read", "tool_name": "k8s_get_pods", "tool_args": {}})
assert r.decision == PolicyDecision.ALLOW
print(f"  Read: {r.decision.value} ({r.reason})")

r = policy_engine.evaluate({"tier": "mutate", "tool_name": "k8s_restart_deployment", "tool_args": {}})
assert r.decision == PolicyDecision.REQUIRE_APPROVAL
print(f"  Mutate: {r.decision.value} ({r.reason})")

r = policy_engine.evaluate({"tier": "destructive", "tool_name": "k8s_delete_namespace", "tool_args": {"namespace": "kube-system"}})
assert r.decision == PolicyDecision.DENY
print(f"  Blocked kube-system delete: {r.decision.value} ({r.reason})")

r = policy_engine.evaluate({"tier": "destructive", "tool_name": "k8s_delete_namespace", "tool_args": {"namespace": "staging"}})
assert r.decision == PolicyDecision.REQUIRE_APPROVAL
print(f"  Destructive (allowed ns): {r.decision.value} ({r.reason})")

# 5. Immutable Audit
print("\n--- Immutable Audit ---")

async def test_audit():
    repo = AuditRepository()
    e1 = await repo.log({
        "user_id": "u1", "org_id": "org1",
        "action": "k8s_get_pods", "tool_name": "k8s_get_pods",
        "tier": "read", "approved": True, "status": "completed",
    })
    assert e1
    print(f"  Entry 1: {e1}")

    e2 = await repo.log({
        "user_id": "u1", "org_id": "org1",
        "action": "k8s_delete_namespace", "tool_name": "k8s_delete_namespace",
        "tool_args": {"namespace": "staging"},
        "tier": "destructive", "approved": False, "status": "denied",
    })
    assert e2
    print(f"  Entry 2: {e2}")

    # Verify chain integrity
    violations = await repo.verify_chain()
    assert violations == [], f"Chain violations: {violations}"
    print(f"  Chain integrity: OK (0 violations)")

    # List entries
    entries = await repo.list(org_id="org1")
    assert len(entries) == 2
    print(f"  List by org: {len(entries)} entries")

    # Update approval
    updated = await repo.update_approval(e2, "admin-user", "Approved after review")
    assert updated == True
    print(f"  Approval update: OK")

    print("\n✅ ALL ENTERPRISE MODULES VERIFIED SUCCESSFULLY")

asyncio.run(test_audit())
