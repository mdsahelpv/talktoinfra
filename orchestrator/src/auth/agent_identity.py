"""Agent-level identity — short-lived JWTs for agent-to-orchestrator auth."""

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.config import settings

logger = logging.getLogger(__name__)


class AgentIdentityManager:
    def __init__(self) -> None:
        self._public_keys: dict[str, str] = {}
        self._tokens: dict[str, dict] = {}

    def register_agent(self, agent_id: str, public_key: str) -> None:
        self._public_keys[agent_id] = public_key

    def issue_agent_token(self, agent_id: str, ttl: int = 3600) -> str:
        try:
            import jwt as pyjwt

            now = datetime.now(timezone.utc)
            payload = {
                "sub": agent_id,
                "iss": "talktoinfra-orchestrator",
                "aud": "talktoinfra-agent",
                "iat": now,
                "exp": now + timedelta(seconds=ttl),
                "jti": str(uuid4()),
                "type": "agent",
            }
            token = pyjwt.encode(payload, settings.auth_jwt_secret, algorithm="HS256")
            self._tokens[agent_id] = {"token": token, "expires_at": payload["exp"]}
            return token
        except ImportError:
            logger.warning("PyJWT not available; returning unsigned token")
            token = f"agent_{agent_id}_{ttl}"
            self._tokens[agent_id] = {"token": token, "expires_at": None}
            return token

    def verify_agent_token(self, token: str) -> dict | None:
        try:
            import jwt as pyjwt

            payload = pyjwt.decode(
                token,
                settings.auth_jwt_secret,
                algorithms=["HS256"],
                audience="talktoinfra-agent",
                issuer="talktoinfra-orchestrator",
            )
            if payload.get("type") != "agent":
                return None
            return payload
        except Exception as exc:
            logger.warning("Agent token verification failed: %s", exc)
            return None

    def get_agent_public_key(self, agent_id: str) -> str | None:
        return self._public_keys.get(agent_id)


agent_identity_manager = AgentIdentityManager()
