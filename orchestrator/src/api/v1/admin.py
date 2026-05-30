"""Admin API — user, org, and policy management."""

from fastapi import APIRouter, Depends, HTTPException

from src.auth.deps import require_permission, AuthContext
from src.auth.rbac import Permission, ROLES, resolve_permissions, Role
from src.storage.repository import UserRepository, OrgRepository

router = APIRouter()
user_repo = UserRepository()
org_repo = OrgRepository()


# ── Users ───────────────────────────────────────────────────────────────

@router.get("/users", tags=["admin"])
async def list_users(
    auth: AuthContext = Depends(require_permission(Permission.USER_READ)),
):
    users = await user_repo.list_by_org(auth.org_id)
    return {"users": users}


@router.get("/users/{user_id}", tags=["admin"])
async def get_user(
    user_id: str,
    auth: AuthContext = Depends(require_permission(Permission.USER_READ)),
):
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}/roles", tags=["admin"])
async def update_user_roles(
    user_id: str,
    roles: list[str],
    auth: AuthContext = Depends(require_permission(Permission.USER_MANAGE)),
):
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    invalid = [r for r in roles if r not in ROLES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid roles: {invalid}")
    await user_repo.upsert({"id": user_id, "roles": roles})
    return {"user_id": user_id, "roles": roles}


# ── Roles ───────────────────────────────────────────────────────────────

@router.get("/roles", tags=["admin"])
async def list_roles(
    auth: AuthContext = Depends(require_permission(Permission.USER_READ)),
):
    return {
        "roles": {
            name: {
                "permissions": sorted(p.value for p in role.permissions),
                "inherited_from": list(role.parents),
            }
            for name, role in ROLES.items()
        }
    }


@router.get("/roles/{role_name}/permissions", tags=["admin"])
async def get_role_permissions(
    role_name: str,
    auth: AuthContext = Depends(require_permission(Permission.USER_READ)),
):
    if role_name not in ROLES:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")
    perms = resolve_permissions([role_name])
    return {
        "role": role_name,
        "permissions": sorted(p.value for p in perms),
    }


# ── Organizations ───────────────────────────────────────────────────────

@router.get("/orgs/{org_id}", tags=["admin"])
async def get_org(
    org_id: str,
    auth: AuthContext = Depends(require_permission(Permission.SETTINGS_READ)),
):
    org = await org_repo.get(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.put("/orgs/{org_id}", tags=["admin"])
async def update_org(
    org_id: str,
    name: str = "",
    domain: str = "",
    auth: AuthContext = Depends(require_permission(Permission.SETTINGS_WRITE)),
):
    await org_repo.upsert({"id": org_id, "name": name, "domain": domain})
    return {"org_id": org_id, "name": name, "domain": domain}


# ── Policies ────────────────────────────────────────────────────────────

@router.get("/policies", tags=["admin"])
async def list_policies(
    auth: AuthContext = Depends(require_permission(Permission.SETTINGS_READ)),
):
    from src.policy.engine import BUILTIN_POLICIES
    return {
        "policies": list(BUILTIN_POLICIES.keys()),
        "total": len(BUILTIN_POLICIES),
    }


@router.get("/policies/{policy_name}/source", tags=["admin"])
async def get_policy_source(
    policy_name: str,
    auth: AuthContext = Depends(require_permission(Permission.SETTINGS_READ)),
):
    from src.policy.engine import BUILTIN_POLICIES
    source = BUILTIN_POLICIES.get(policy_name)
    if not source:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_name}' not found")
    return {"name": policy_name, "source": source}
