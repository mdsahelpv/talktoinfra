"""
Security middleware for JWT validation and user authentication.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from functools import lru_cache

import httpx
import structlog
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import get_settings

logger = structlog.get_logger()
security = HTTPBearer()


class UserContext:
    """User context extracted from JWT token."""

    def __init__(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: List[str],
        permissions: List[str],
        is_active: bool = True,
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles
        self.permissions = permissions
        self.is_active = is_active
        self.request_time = datetime.utcnow()

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return "admin" in self.roles or "administrator" in self.roles

    @property
    def is_operator(self) -> bool:
        """Check if user has operator role."""
        return "operator" in self.roles or self.is_admin

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions or self.is_admin

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "is_admin": self.is_admin,
        }


@lru_cache()
def get_jwt_settings() -> Dict[str, str]:
    """Get JWT configuration settings."""
    settings = get_settings()
    return {
        "secret": settings.jwt_secret,
        "algorithm": settings.jwt_algorithm,
        "gateway_url": settings.api_gateway_url,
        "verify_with_gateway": settings.verify_token_with_gateway,
    }


async def verify_token_with_gateway(token: str) -> Optional[Dict[str, Any]]:
    """Verify token with API Gateway."""
    settings = get_jwt_settings()
    gateway_url = settings["gateway_url"]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{gateway_url}/api/v1/auth/verify",
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 200:
                return response.json()
            return None
    except httpx.RequestError as e:
        logger.error("gateway_verify_failed", error=str(e))
        return None


async def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT token locally."""
    settings = get_jwt_settings()

    try:
        payload = jwt.decode(
            token,
            settings["secret"],
            algorithms=[settings["algorithm"]],
        )
        return payload
    except JWTError as e:
        logger.error("jwt_decode_failed", error=str(e))
        return None


async def validate_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> UserContext:
    """Validate JWT token and extract user context.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        UserContext object with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials

    # Try gateway verification first if enabled
    settings = get_jwt_settings()
    payload = None

    if settings["verify_with_gateway"]:
        payload = await verify_token_with_gateway(token)

    # Fall back to local verification
    if payload is None:
        payload = await decode_jwt_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user information
    user_id = payload.get("sub") or payload.get("user_id")
    username = payload.get("username") or payload.get("preferred_username") or user_id
    email = payload.get("email") or ""
    roles = payload.get("roles", [])
    permissions = payload.get("permissions", [])
    is_active = payload.get("is_active", True)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token: missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive",
        )

    return UserContext(
        user_id=user_id,
        username=username,
        email=email,
        roles=roles,
        permissions=permissions,
        is_active=is_active,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> UserContext:
    """Dependency to get current authenticated user."""
    return await validate_token(credentials)


async def require_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    """Dependency to require admin role.

    TODO: Implement proper authorization in future.
    Currently all authenticated users are treated as admin.

    Args:
        user: Current user context

    Returns:
        UserContext if user is authenticated (admin check bypassed)
    """
    # TODO: Re-enable admin check when implementing proper authorization
    # if not user.is_admin:
    #     logger.warning(
    #         "admin_access_denied",
    #         user_id=user.user_id,
    #         username=user.username,
    #         required_permission="admin",
    #     )
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Admin privileges required for this operation",
    #     )
    return user


async def require_operator(
    user: UserContext = Depends(get_current_user),
) -> UserContext:
    """Dependency to require operator or admin role.

    TODO: Implement proper authorization in future.
    Currently all authenticated users are treated as operators.
    """
    # TODO: Re-enable operator check when implementing proper authorization
    # if not user.is_operator:
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Operator privileges required for this operation",
    #     )
    return user


class SecurityMiddleware:
    """Middleware to add security headers and request context."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Add security headers to response
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                # Security headers
                security_headers = [
                    (b"X-Content-Type-Options", b"nosniff"),
                    (b"X-Frame-Options", b"DENY"),
                    (b"X-XSS-Protection", b"1; mode=block"),
                    (b"Referrer-Policy", b"strict-origin-when-cross-origin"),
                    (
                        b"Permissions-Policy",
                        b"geolocation=(), microphone=(), camera=()",
                    ),
                ]

                # Only add HSTS in production (HTTPS)
                settings = get_settings()
                if not settings.debug:
                    security_headers.append(
                        (
                            b"Strict-Transport-Security",
                            b"max-age=31536000; includeSubDomains",
                        )
                    )
                    # Basic CSP for production
                    security_headers.append(
                        (b"Content-Security-Policy", b"default-src 'self'"),
                    )

                headers.extend(security_headers)
                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_with_headers)


async def audit_log(
    action: str,
    user: UserContext,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
) -> None:
    """Log an auditable action.

    Args:
        action: The action being performed (e.g., "scan_create", "host_delete")
        user: User context
        resource_type: Type of resource being accessed
        resource_id: Optional resource identifier
        details: Additional details about the action
        success: Whether the action succeeded
    """
    log_data = {
        "event": "audit",
        "action": action,
        "user_id": user.user_id,
        "username": user.username,
        "resource_type": resource_type,
        "success": success,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if resource_id:
        log_data["resource_id"] = resource_id

    if details:
        log_data["details"] = details

    if success:
        logger.info("audit_action", **log_data)
    else:
        logger.warning("audit_action_failed", **log_data)


def is_excluded_network(ip_range: str, excluded_networks: List[str]) -> bool:
    """Check if an IP range overlaps with excluded networks.

    Args:
        ip_range: CIDR notation IP range
        excluded_networks: List of excluded CIDR ranges

    Returns:
        True if the IP range overlaps with any excluded network
    """
    import ipaddress

    try:
        target_network = ipaddress.ip_network(ip_range, strict=False)

        for excluded in excluded_networks:
            try:
                excluded_network = ipaddress.ip_network(excluded, strict=False)

                # Check for overlap
                if target_network.overlaps(excluded_network):
                    return True
            except ValueError:
                continue

        return False
    except ValueError:
        return True  # Treat invalid networks as excluded for safety


async def validate_network_access(
    ip_range: str,
    user: UserContext,
    require_approval_threshold: int = 4096,
) -> Dict[str, Any]:
    """Validate network access and check exclusions.

    Args:
        ip_range: CIDR notation IP range
        user: UserContext
        require_approval_threshold: Network size threshold requiring admin approval

    Returns:
        Dict with validation results including requires_admin_approval flag

    Raises:
        HTTPException: If network is excluded or user lacks permissions
    """
    import ipaddress

    settings = get_settings()

    try:
        network = ipaddress.ip_network(ip_range, strict=False)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid IP range: {str(e)}",
        )

    # Check exclusions
    if is_excluded_network(ip_range, settings.excluded_networks):
        logger.warning(
            "excluded_network_access_attempt",
            user_id=user.user_id,
            username=user.username,
            ip_range=ip_range,
        )
        raise HTTPException(
            status_code=403,
            detail="This network range is excluded from scanning",
        )

    result = {
        "network": str(network),
        "num_addresses": network.num_addresses,
        "requires_admin_approval": False,
        "requires_operator": False,
    }

    # TODO: Implement proper authorization in future
    # Currently bypassing network size restrictions for all authenticated users
    # Check if network size requires admin approval
    # if network.num_addresses > require_approval_threshold:
    #     result["requires_admin_approval"] = True
    #     if not user.is_admin:
    #         logger.warning(
    #             "large_scan_requires_approval",
    #             user_id=user.user_id,
    #             username=user.username,
    #             ip_range=ip_range,
    #             num_addresses=network.num_addresses,
    #         )
    #         raise HTTPException(
    #             status_code=403,
    #             detail=f"Network too large ({network.num_addresses} addresses). Admin approval required.",
    #         )

    # Check if scan requires operator role for non-trivial sizes
    # if network.num_addresses > 256:
    #     result["requires_operator"] = True
    #     if not user.is_operator:
    #         raise HTTPException(
    #             status_code=403,
    #             detail="Operator role required for scans larger than /24",
    #         )

    return result
