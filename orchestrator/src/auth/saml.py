"""SAML 2.0 authentication provider — supports IdP-initiated SSO."""

import logging
from dataclasses import dataclass, field

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SAMLResponse:
    user_id: str
    email: str
    name: str
    attributes: dict = field(default_factory=dict)


class SAMLProvider:
    def __init__(self) -> None:
        self.metadata_url = settings.auth_saml_metadata_url
        self.entity_id = settings.auth_saml_entity_id
        self.acs_url = settings.auth_saml_acs_url

    async def saml_metadata(self) -> str:
        """Return SAML metadata XML for this service provider."""
        return f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="{self.entity_id}">
  <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                  Location="{self.acs_url}"
                                  index="0"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>"""

    async def saml_acs(self, saml_response: str) -> SAMLResponse | None:
        """Process SAML assertion and return user info."""
        try:
            import xml.etree.ElementTree as ET
            import base64
            import zlib

            decoded = base64.b64decode(saml_response)
            try:
                decoded = zlib.decompress(decoded)
            except zlib.error:
                pass

            root = ET.fromstring(decoded)
            ns = {
                "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
                "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
            }

            assertion = root.find(".//saml:Assertion", ns)
            if assertion is None:
                return None

            subject = assertion.find(".//saml:Subject/saml:NameID", ns)
            user_id = subject.text if subject is not None else ""

            attrs = {}
            for attr in assertion.findall(".//saml:Attribute", ns):
                name = attr.get("Name", "")
                vals = [v.text or "" for v in attr.findall("saml:AttributeValue", ns)]
                if vals:
                    attrs[name] = vals[0]

            return SAMLResponse(
                user_id=user_id,
                email=attrs.get("email", attrs.get("mail", user_id)),
                name=attrs.get("name", attrs.get("displayName", user_id)),
                attributes=attrs,
            )
        except Exception as exc:
            logger.error("SAML ACS processing failed: %s", exc)
            return None


saml_provider = SAMLProvider()
