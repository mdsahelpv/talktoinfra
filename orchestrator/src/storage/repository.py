"""Data access repositories — including immutable Merkle-chain audit log."""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, func

from src.config import settings
from src.storage.database import async_session
from src.storage.models import AuditModel, UserModel, OrgModel


# ── Immutable Audit Repository ──────────────────────────────────────────

def _hash_block(block_data: dict, prev_hash: str) -> str:
    """SHA-256 hash of block content + previous hash."""
    raw = json.dumps(block_data, sort_keys=True, default=str) + prev_hash
    return hashlib.sha256(raw.encode()).hexdigest()


def _sign_block(chain_hash: str) -> str:
    """Optional HMAC signature using server secret."""
    return hmac.new(
        settings.auth_jwt_secret.encode(),
        chain_hash.encode(),
        hashlib.sha256,
    ).hexdigest()


class AuditRepository:
    async def log(self, entry: dict) -> str:
        entry_id = str(uuid4())
        timestamp = datetime.now(timezone.utc)

        # Get the last block to chain to
        async with async_session() as session:
            last_block = await session.execute(
                select(AuditModel).order_by(AuditModel.block_index.desc()).limit(1)
            )
            last = last_block.scalar_one_or_none()
            prev_hash = last.chain_hash if last else "genesis"
            block_index = (last.block_index + 1) if last else 0

        block_data = {
            "id": entry_id,
            "session_id": entry.get("session_id", ""),
            "user_id": entry.get("user_id", ""),
            "org_id": entry.get("org_id", ""),
            "action": entry.get("action", ""),
            "tool_name": entry.get("tool_name", ""),
            "tier": entry.get("tier", ""),
            "approved": entry.get("approved", False),
            "approved_by": entry.get("approved_by", ""),
            "status": entry.get("status", ""),
            "error": entry.get("error", ""),
            "timestamp": timestamp.isoformat(),
        }
        chain_hash = _hash_block(block_data, prev_hash)
        signature = _sign_block(chain_hash) if settings.auth_jwt_secret != "change-me-in-production" else ""

        async with async_session() as session:
            model = AuditModel(
                id=entry_id,
                session_id=entry.get("session_id", ""),
                user_id=entry.get("user_id", ""),
                org_id=entry.get("org_id", ""),
                action=entry.get("action", ""),
                parameters=entry.get("parameters", {}),
                tier=entry.get("tier", ""),
                tool_name=entry.get("tool_name", ""),
                tool_args=entry.get("tool_args", {}),
                approved=entry.get("approved", False),
                approved_by=entry.get("approved_by", ""),
                approval_note=entry.get("approval_note", ""),
                status=entry.get("status", ""),
                result=entry.get("result", ""),
                duration_ms=entry.get("duration_ms", 0),
                error=entry.get("error", ""),
                block_index=block_index,
                prev_hash=prev_hash,
                chain_hash=chain_hash,
                signature=signature,
                timestamp=timestamp,
            )
            session.add(model)
            await session.commit()
        return entry_id

    async def verify_chain(self) -> list[dict]:
        """Walk the chain and verify integrity. Returns any broken links."""
        async with async_session() as session:
            blocks = await session.execute(
                select(AuditModel).order_by(AuditModel.block_index.asc())
            )
            blocks = blocks.scalars().all()

        violations = []
        prev = "genesis"
        for b in blocks:
            expected_hash = _hash_block(
                {
                    "id": b.id,
                    "session_id": b.session_id,
                    "user_id": b.user_id,
                    "org_id": b.org_id,
                    "action": b.action,
                    "tool_name": b.tool_name,
                    "tier": b.tier,
                    "approved": b.approved,
                    "approved_by": b.approved_by,
                    "status": b.status,
                    "error": b.error,
                    "timestamp": b.timestamp.replace(tzinfo=timezone.utc).isoformat() if b.timestamp else "",
                },
                prev,
            )
            if expected_hash != b.chain_hash:
                violations.append({
                    "block_index": b.block_index,
                    "expected_hash": expected_hash,
                    "stored_hash": b.chain_hash,
                })
            prev = b.chain_hash
        return violations

    async def list(self, session_id: str = "", org_id: str = "", limit: int = 50, offset: int = 0) -> list[dict]:
        async with async_session() as session:
            stmt = select(AuditModel).order_by(AuditModel.timestamp.desc())
            if session_id:
                stmt = stmt.where(AuditModel.session_id == session_id)
            if org_id:
                stmt = stmt.where(AuditModel.org_id == org_id)
            stmt = stmt.offset(offset).limit(limit)
            result = await session.execute(stmt)
            entries = result.scalars().all()
            return [
                {
                    "id": e.id,
                    "session_id": e.session_id,
                    "user_id": e.user_id,
                    "org_id": e.org_id,
                    "action": e.action,
                    "tool_name": e.tool_name,
                    "tier": e.tier,
                    "approved": e.approved,
                    "approved_by": e.approved_by,
                    "status": e.status,
                    "error": e.error,
                    "block_index": e.block_index,
                    "chain_hash": e.chain_hash[:16] + "...",
                    "timestamp": e.timestamp.isoformat() if e.timestamp else "",
                }
                for e in entries
            ]

    async def update_approval(self, entry_id: str, approved_by: str, note: str = "") -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(AuditModel).where(AuditModel.id == entry_id)
            )
            entry = result.scalar_one_or_none()
            if not entry:
                return False
            entry.approved = True
            entry.approved_by = approved_by
            entry.approval_note = note
            entry.status = "approved"
            await session.commit()
            return True

    async def count(self, session_id: str = "", org_id: str = "") -> int:
        async with async_session() as session:
            stmt = select(func.count(AuditModel.id))
            if session_id:
                stmt = stmt.where(AuditModel.session_id == session_id)
            if org_id:
                stmt = stmt.where(AuditModel.org_id == org_id)
            result = await session.execute(stmt)
            return result.scalar() or 0


# ── User Repository ─────────────────────────────────────────────────────

class UserRepository:
    async def upsert(self, user_data: dict) -> str:
        async with async_session() as session:
            existing = await session.execute(
                select(UserModel).where(UserModel.id == user_data["id"])
            )
            user = existing.scalar_one_or_none()
            if user:
                for k, v in user_data.items():
                    setattr(user, k, v)
                user.last_login = datetime.now(timezone.utc)
            else:
                user = UserModel(
                    id=user_data["id"],
                    email=user_data.get("email", ""),
                    name=user_data.get("name", ""),
                    org_id=user_data.get("org_id", ""),
                    roles=user_data.get("roles", ["viewer"]),
                )
                session.add(user)
            await session.commit()
            return user.id

    async def get(self, user_id: str) -> dict | None:
        async with async_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return None
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "org_id": user.org_id,
                "roles": user.roles,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else "",
            }

    async def list_by_org(self, org_id: str) -> list[dict]:
        async with async_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.org_id == org_id)
            )
            users = result.scalars().all()
            return [{"id": u.id, "email": u.email, "name": u.name, "roles": u.roles} for u in users]


# ── Organization Repository ─────────────────────────────────────────────

class OrgRepository:
    async def upsert(self, org_data: dict) -> str:
        async with async_session() as session:
            existing = await session.execute(
                select(OrgModel).where(OrgModel.id == org_data["id"])
            )
            org = existing.scalar_one_or_none()
            if org:
                for k, v in org_data.items():
                    setattr(org, k, v)
            else:
                org = OrgModel(
                    id=org_data["id"],
                    name=org_data.get("name", ""),
                    domain=org_data.get("domain", ""),
                )
                session.add(org)
            await session.commit()
            return org.id

    async def get(self, org_id: str) -> dict | None:
        async with async_session() as session:
            result = await session.execute(
                select(OrgModel).where(OrgModel.id == org_id)
            )
            org = result.scalar_one_or_none()
            if not org:
                return None
            return {
                "id": org.id,
                "name": org.name,
                "domain": org.domain,
                "domain_verified": org.domain_verified,
                "settings": org.settings,
            }
