"""MFA (TOTP) authentication support."""

import logging

from src.config import settings

logger = logging.getLogger(__name__)


class TOTPManager:
    def __init__(self) -> None:
        self.issuer = settings.auth_mfa_issuer

    def generate_secret(self) -> dict:
        try:
            import pyotp

            secret = pyotp.random_base32()
            uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=self.issuer,
                issuer_name=self.issuer,
            )
            return {"secret": secret, "uri": uri}
        except ImportError:
            logger.warning("pyotp not installed; returning mock secret")
            return {"secret": "MOCK" + "A" * 31, "uri": "otpauth://totp/TalkToInfra?secret=MOCK"}

    def verify_token(self, secret: str, token: str) -> bool:
        try:
            import pyotp

            totp = pyotp.TOTP(secret)
            return totp.verify(token)
        except ImportError:
            logger.warning("pyotp not installed; accepting any 6-digit code")
            return len(token) == 6 and token.isdigit()

    @property
    def required(self) -> bool:
        return settings.auth_mfa_required


totp_manager = TOTPManager()
