"""FastAPI dependency injection for authentication and authorization."""

from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.config import settings
from src.auth.jwt import decode_token
from src.auth.oidc import oidc_provider
from src.auth.rbac import has_permission, Permission


class AuthContext:
    def __init__(
        self,
        user_id: str,
        email: str = "",
        roles: list[str] | None = None,
        org_id: str = "",
        token_type: str = "anonymous",
    ):
        self.user_id = user_id
        self.email = email
        self.roles = roles or ["viewer"]
        self.org_id = org_id
        self.token_type = token_type

    def has_permission(self, permission: Permission) -> bool:
        return has_permission(self.roles, permission)


_bearer = HTTPBearer(auto_error=False)


async def get_auth_context(
    authorization: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_api_key: str = Header(default=""),
) -> AuthContext:
    if not settings.enable_auth:
        return AuthContext("anonymous", roles=["admin"], token_type="anonymous")

    # 1. Try OIDC bearer token
    if authorization and authorization.scheme.lower() == "bearer":
        token = authorization.credentials

        # Try JWT (internal tokens)
        try:
            payload = decode_token(token)
            return AuthContext(
                user_id=payload.get("sub", "unknown"),
                roles=payload.get("roles", ["viewer"]),
                org_id=payload.get("org_id", ""),
                token_type="jwt",
            )
        except Exception:
            pass

        # Try OIDC (external IdP tokens)
        user_info = await oidc_provider.validate_token(token)
        if user_info:
            return AuthContext(
                user_id=user_info.sub,
                email=user_info.email,
                roles=user_info.groups or ["viewer"],
                org_id=user_info.org_id,
                token_type="oidc",
            )

    # 2. Fallback: API key
    valid_keys = [k.strip() for k in settings.api_keys.split(",") if k.strip()]
    if x_api_key and x_api_key in valid_keys:
        return AuthContext(
            user_id=f"apikey-{x_api_key[:8]}",
            roles=["operator"],
            token_type="api_key",
        )

    raise HTTPException(status_code=401, detail="Authentication required")


def require_permission(permission: Permission):
    async def _check(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not auth.has_permission(permission):
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission.value}")
        return auth
    return _check
