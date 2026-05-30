"""OIDC provider abstraction. Supports Okta, Entra ID, Google Workspace, and generic OIDC."""

from dataclasses import dataclass

import httpx

from src.config import settings


@dataclass
class OIDCUserInfo:
    sub: str
    email: str
    name: str
    groups: list[str]
    org_id: str = ""


class OIDCProvider:
    def __init__(self) -> None:
        self._jwks_cache: dict[str, list[dict]] = {}
        self._config_cache: dict[str, dict] = {}

    async def get_public_keys(self) -> list[dict]:
        if settings.auth_oidc_jwks_url in self._jwks_cache:
            return self._jwks_cache[settings.auth_oidc_jwks_url]
        async with httpx.AsyncClient() as client:
            resp = await client.get(settings.auth_oidc_jwks_url)
            resp.raise_for_status()
            data = resp.json()
            keys = data.get("keys", [])
            self._jwks_cache[settings.auth_oidc_jwks_url] = keys
            return keys

    async def validate_token(self, token: str) -> OIDCUserInfo | None:
        try:
            import jwt as pyjwt
            keys = await self.get_public_keys()
            header = pyjwt.get_unverified_header(token)
            kid = header.get("kid")

            matching_key = None
            for k in keys:
                if k.get("kid") == kid:
                    matching_key = k
                    break
            if not matching_key:
                return None

            public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(matching_key)
            payload = pyjwt.decode(
                token,
                public_key,
                algorithms=["RS256", "RS384", "RS512"],
                audience=settings.auth_oidc_audience,
                issuer=settings.auth_oidc_issuer,
                options={"verify_exp": True},
            )
            return OIDCUserInfo(
                sub=payload.get("sub", ""),
                email=payload.get("email", "") or payload.get("preferred_username", ""),
                name=payload.get("name", ""),
                groups=payload.get("groups", []) or payload.get("roles", []),
                org_id=self._extract_org(payload),
            )
        except Exception:
            return None

    def _extract_org(self, payload: dict) -> str:
        for field in settings.auth_oidc_org_field.split(","):
            parts = field.strip().split(".")
            val: dict | str = payload
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p, "")
                else:
                    break
            if val:
                return str(val)
        return ""


oidc_provider = OIDCProvider()
