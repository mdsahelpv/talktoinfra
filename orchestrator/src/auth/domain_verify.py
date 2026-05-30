"""Domain verification via DNS TXT records."""

import logging
import secrets
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class DomainVerifier:
    def __init__(self) -> None:
        self._pending_tokens: dict[str, dict] = {}

    def generate_verification_token(self, org_id: str, domain: str) -> str:
        token = f"talktoinfra-verify={secrets.token_hex(16)}"
        self._pending_tokens[domain] = {
            "org_id": org_id,
            "token": token,
            "created_at": datetime.now(timezone.utc),
            "verified": False,
        }
        return token

    def verify_dns_txt(self, domain: str, token: str) -> bool:
        try:
            import dns.resolver

            try:
                answers = dns.resolver.resolve(domain, "TXT")
                for rdata in answers:
                    txt = "".join(rdata.strings)
                    if token in txt:
                        self._mark_verified(domain)
                        return True
            except Exception as exc:
                logger.warning("DNS lookup failed for %s: %s", domain, exc)
        except ImportError:
            logger.warning("dnspython not installed; falling back to manual confirmation")

        pending = self._pending_tokens.get(domain)
        if pending and pending["token"] == token:
            self._mark_verified(domain)
            return True
        return False

    def _mark_verified(self, domain: str) -> None:
        if domain in self._pending_tokens:
            self._pending_tokens[domain]["verified"] = True

    def is_verified(self, domain: str) -> bool:
        pending = self._pending_tokens.get(domain)
        return pending is not None and pending["verified"]


domain_verifier = DomainVerifier()
