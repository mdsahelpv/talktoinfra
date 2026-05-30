from datetime import datetime, timedelta, timezone

import jwt as pyjwt

from src.config import settings

ALGORITHM = "HS256"


def create_token(
    user_id: str,
    roles: list[str],
    org_id: str = "",
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "roles": roles,
        "org_id": org_id,
        "iat": now,
        "exp": now + (expires_delta or timedelta(hours=1)),
        "iss": "talktoinfra-orchestrator",
    }
    return pyjwt.encode(payload, settings.auth_jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return pyjwt.decode(
        token,
        settings.auth_jwt_secret,
        algorithms=[ALGORITHM],
        issuer="talktoinfra-orchestrator",
    )
