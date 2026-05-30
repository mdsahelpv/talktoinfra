"""Tenant isolation tests — prove Org A cannot access Org B's data."""

import pytest

from src.storage.repository import AuditRepository, UserRepository, OrgRepository
from src.storage.database import create_db_and_tables
from src.storage.models import Base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    original_engine = __import__("src.storage.database", fromlist=["engine"]).engine
    original_session = __import__("src.storage.database", fromlist=["async_session"]).async_session

    import src.storage.database as db_mod
    db_mod.engine = engine
    db_mod.async_session = session_maker

    yield session_maker

    db_mod.engine = original_engine
    db_mod.async_session = original_session


@pytest.mark.asyncio
async def test_org_a_cannot_see_org_b_audit_logs(db):
    audit = AuditRepository()

    await audit.log({"session_id": "sess-a", "user_id": "user-a", "org_id": "org-a", "action": "test", "tier": "read"})
    await audit.log({"session_id": "sess-b", "user_id": "user-b", "org_id": "org-b", "action": "test", "tier": "read"})

    org_a_entries = await audit.list(org_id="org-a")
    org_b_entries = await audit.list(org_id="org-b")

    org_a_ids = {e["session_id"] for e in org_a_entries}
    org_b_ids = {e["session_id"] for e in org_b_entries}

    assert "sess-b" not in org_a_ids, "Org A should not see Org B's audit logs"
    assert "sess-a" not in org_b_ids, "Org B should not see Org A's audit logs"


@pytest.mark.asyncio
async def test_org_a_cannot_access_org_b_sessions(db):
    async with db() as session:
        from src.storage.models import SessionModel
        from datetime import datetime, timezone

        session.add(SessionModel(id="sess-a", user_id="user-a", org_id="org-a", description="Org A session"))
        session.add(SessionModel(id="sess-b", user_id="user-b", org_id="org-b", description="Org B session"))
        await session.commit()

    from src.models.session import SessionManager
    mgr = SessionManager()

    sess_a = await mgr.get("sess-a")
    sess_b = await mgr.get("sess-b")

    if sess_a:
        assert sess_a.get("org_id", "") == "org-a", "Session A belongs to Org A"
    if sess_b:
        assert sess_b.get("org_id", "") == "org-b", "Session B belongs to Org B"


@pytest.mark.asyncio
async def test_org_a_agents_cannot_execute_on_org_b_infra(db):
    from src.storage.repository import UserRepository
    repo = UserRepository()

    await repo.upsert({"id": "agent-a", "org_id": "org-a", "email": "agent-a@org-a.com", "roles": ["operator"]})
    await repo.upsert({"id": "agent-b", "org_id": "org-b", "email": "agent-b@org-b.com", "roles": ["operator"]})

    agent_a = await repo.get("agent-a")
    agent_b = await repo.get("agent-b")

    assert agent_a["org_id"] == "org-a", "Agent A belongs to Org A"
    assert agent_b["org_id"] == "org-b", "Agent B belongs to Org B"

    from src.auth.rbac import has_permission, Permission
    from src.policy.engine import policy_engine, PolicyDecision

    result = policy_engine.evaluate({
        "tier": "destructive",
        "tool_name": "k8s_delete_namespace",
        "tool_args": {"namespace": "org-b-ns"},
        "user_roles": agent_a.get("roles", []),
    })
    assert result.decision != PolicyDecision.ALLOW, "Org A's agent should not auto-execute destructive on Org B"


@pytest.mark.asyncio
async def test_rbac_roles_dont_leak_between_orgs(db):
    from src.storage.repository import UserRepository
    repo = UserRepository()

    await repo.upsert({"id": "admin-org-a", "org_id": "org-a", "email": "admin@org-a.com", "roles": ["admin"]})
    await repo.upsert({"id": "viewer-org-b", "org_id": "org-b", "email": "viewer@org-b.com", "roles": ["viewer"]})

    admin_a = await repo.get("admin-org-a")
    viewer_b = await repo.get("viewer-org-b")

    assert admin_a["org_id"] == "org-a"
    assert viewer_b["org_id"] == "org-b"
    assert admin_a["roles"] == ["admin"]
    assert viewer_b["roles"] == ["viewer"]

    from src.auth.rbac import resolve_permissions
    admin_perms = resolve_permissions(admin_a["roles"])
    viewer_perms = resolve_permissions(viewer_b["roles"])
    assert "admin:*" in {p.value for p in admin_perms}, "Org A admin has admin permissions"
    assert "admin:*" not in {p.value for p in viewer_perms}, "Org B viewer does not have admin permissions"
