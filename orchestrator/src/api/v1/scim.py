"""SCIM 2.0 endpoints for user provisioning."""

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from src.storage.repository import UserRepository
from src.storage.database import async_session
from src.storage.models import UserModel
from sqlalchemy import select, func

router = APIRouter()
user_repo = UserRepository()

SCHEMAS = {
    "User": "urn:ietf:params:scim:schemas:core:2.0:User",
    "ListResponse": "urn:ietf:params:scim:api:messages:2.0:ListResponse",
}


def _to_scim(user: dict) -> dict:
    return {
        "schemas": [SCHEMAS["User"]],
        "id": user["id"],
        "userName": user.get("email", user["id"]),
        "name": {"formatted": user.get("name", "")},
        "emails": [{"value": user.get("email", ""), "primary": True}],
        "active": user.get("is_active", True),
        "meta": {
            "resourceType": "User",
            "location": f"/scim/v2/Users/{user['id']}",
        },
    }


@router.post("/scim/v2/Users", status_code=201)
async def create_user(data: dict[str, Any]):
    user_id = data.get("id", str(uuid4()))
    name = data.get("name", {})
    emails = data.get("emails", [])
    email = emails[0]["value"] if emails else name.get("formatted", user_id)
    await user_repo.upsert({
        "id": user_id,
        "email": email,
        "name": name.get("formatted", ""),
        "roles": data.get("roles", ["viewer"]),
    })
    user = await user_repo.get(user_id)
    return _to_scim(user or {"id": user_id, "email": email})


@router.get("/scim/v2/Users/{user_id}")
async def get_user(user_id: str):
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_scim(user)


@router.put("/scim/v2/Users/{user_id}")
async def update_user(user_id: str, data: dict[str, Any]):
    existing = await user_repo.get(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    name = data.get("name", {})
    emails = data.get("emails", [])
    email = emails[0]["value"] if emails else data.get("userName", existing["email"])
    await user_repo.upsert({
        "id": user_id,
        "email": email,
        "name": name.get("formatted", data.get("displayName", existing["name"])),
        "roles": data.get("roles", existing["roles"]),
    })
    user = await user_repo.get(user_id)
    return _to_scim(user or existing)


@router.patch("/scim/v2/Users/{user_id}")
async def patch_user(user_id: str, data: dict[str, Any]):
    existing = await user_repo.get(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    ops = data.get("Operations", [])
    for op in ops:
        path = op.get("path", "")
        value = op.get("value", {})
        if op.get("op", "").lower() in ("replace", "add"):
            if path == "active":
                existing["is_active"] = value
            elif path == "userName":
                existing["email"] = value
            elif path == "name.formatted":
                existing["name"] = value
            elif isinstance(value, dict):
                existing.update(value)
        elif op.get("op", "").lower() == "remove":
            if path == "active":
                existing["is_active"] = False
    await user_repo.upsert(existing)
    user = await user_repo.get(user_id)
    return _to_scim(user or existing)


@router.delete("/scim/v2/Users/{user_id}", status_code=204)
async def deactivate_user(user_id: str):
    existing = await user_repo.get(user_id)
    if existing:
        existing["is_active"] = False
        await user_repo.upsert(existing)
    return None


@router.get("/scim/v2/Users")
async def list_users(
    filter: str = "",
    startIndex: int = Query(default=1, ge=1),
    count: int = Query(default=50, ge=0, le=200),
):
    offset = max(0, startIndex - 1)
    limit = count
    async with async_session() as session:
        stmt = select(UserModel).order_by(UserModel.created_at.desc())
        if filter:
            stmt = stmt.where(UserModel.email.ilike(f"%{filter}%"))
        total_stmt = select(func.count(UserModel.id))
        if filter:
            total_stmt = total_stmt.where(UserModel.email.ilike(f"%{filter}%"))
        total_result = await session.execute(total_stmt)
        total = total_result.scalar() or 0
        stmt = stmt.offset(offset).limit(limit)
        result = await session.execute(stmt)
        users = result.scalars().all()
    resources = [
        _to_scim({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "is_active": u.is_active,
        })
        for u in users
    ]
    return {
        "schemas": [SCHEMAS["ListResponse"]],
        "totalResults": total,
        "startIndex": startIndex,
        "itemsPerPage": limit,
        "Resources": resources,
    }
