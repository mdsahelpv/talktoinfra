"""
Authentication utilities for JWT tokens.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from jose import JWTError, jwt
from fastapi import HTTPException, status


def create_token(
    user_id: str,
    username: str,
    roles: List[str],
    secret: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a new JWT token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode = {
        "sub": user_id,
        "username": username,
        "roles": roles,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    return jwt.encode(to_encode, secret, algorithm=algorithm)


def verify_token(token: str, secret: str, algorithm: str = "HS256") -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])

        # Check expiration
        exp = payload.get("exp")
        if exp is None or datetime.utcnow() > datetime.fromtimestamp(exp):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            )

        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def has_role(payload: dict, required_role: str) -> bool:
    """Check if user has a specific role."""
    roles = payload.get("roles", [])
    return required_role in roles or "admin" in roles
