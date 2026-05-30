"""SQLAlchemy ORM models — extended for enterprise RBAC and immutable audit."""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON, BigInteger
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


# ── Sessions ────────────────────────────────────────────────────────────

class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, default="", index=True)
    org_id = Column(String, default="", index=True)
    description = Column(String, default="")
    messages = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="active")


# ── Immutable Audit Log (Merkle-chain) ──────────────────────────────────

class AuditModel(Base):
    __tablename__ = "audit_log"

    id = Column(String, primary_key=True)
    session_id = Column(String, default="", index=True)
    user_id = Column(String, default="", index=True)
    org_id = Column(String, default="", index=True)

    # Action details
    action = Column(String, default="")
    parameters = Column(JSON, default=dict)
    tier = Column(String, default="")
    tool_name = Column(String, default="")
    tool_args = Column(JSON, default=dict)

    # Approval
    approved = Column(Boolean, default=False)
    approved_by = Column(String, default="")
    approval_note = Column(String, default="")
    status = Column(String, default="")

    # Result
    result = Column(Text, default="")
    duration_ms = Column(Integer, default=0)
    error = Column(String, default="")

    # ── Merkle-chain integrity ──
    block_index = Column(BigInteger, default=0, index=True)
    prev_hash = Column(String, default="")        # sha256 of previous block
    chain_hash = Column(String, default="")        # sha256 of this block
    signature = Column(String, default="")          # HMAC signature (optional)

    # Timestamp
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


# ── RBAC ─────────────────────────────────────────────────────────────────

class UserModel(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, default="", index=True)
    name = Column(String, default="")
    org_id = Column(String, default="", index=True)
    roles = Column(JSON, default=list)       # ["admin", "operator"]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class OrgModel(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True)
    name = Column(String, default="")
    domain = Column(String, default="", index=True)
    domain_verified = Column(Boolean, default=False)
    sso_config = Column(JSON, default=dict)   # OIDC/SAML settings per org
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
