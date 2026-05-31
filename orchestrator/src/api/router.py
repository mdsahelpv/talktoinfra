from fastapi import APIRouter

from src.api.v1.chat import router as chat_router
from src.api.v1.sessions import router as sessions_router
from src.api.v1.tools import router as tools_router
from src.api.v1.agents import router as agents_router
from src.api.v1.agent_register import router as agent_register_router
from src.api.v1.audit import router as audit_router
from src.api.v1.health import router as health_router
from src.api.v1.admin import router as admin_router
from src.api.v1.discover import router as discover_router
from src.api.v1.network_scan import router as network_scan_router

# -- Enterprise Phase 1h: SCIM + SAML routers --
from src.api.v1.scim import router as scim_router
from src.auth.saml import saml_provider

api_router = APIRouter()

api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_router.include_router(tools_router, prefix="/tools", tags=["tools"])
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(agent_register_router, prefix="/agents", tags=["agents"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(discover_router, prefix="", tags=["discovery"])
api_router.include_router(network_scan_router, prefix="", tags=["network-scan"])
api_router.include_router(health_router, prefix="/health", tags=["health"])

# -- Enterprise Phase 1h: SCIM router --
api_router.include_router(scim_router, tags=["scim"])

# -- Enterprise Phase 1h: SAML endpoints --
from fastapi import Request, Response
from fastapi.responses import HTMLResponse


@api_router.get("/saml/metadata", tags=["saml"])
async def saml_metadata():
    xml = await saml_provider.saml_metadata()
    return Response(content=xml, media_type="application/xml")


@api_router.post("/saml/acs", tags=["saml"])
async def saml_acs(request: Request):
    form = await request.form()
    saml_response = form.get("SAMLResponse", "")
    result = await saml_provider.saml_acs(saml_response)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="SAML authentication failed")
    return {"user_id": result.user_id, "email": result.email, "name": result.name}
