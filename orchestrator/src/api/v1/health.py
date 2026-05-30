from fastapi import APIRouter, Depends

from src.config import settings
from src.auth.deps import get_auth_context, AuthContext

router = APIRouter()


@router.get("")
async def health_check(auth: AuthContext = Depends(get_auth_context)):
    return {
        "service": "talktoinfra-orchestrator",
        "version": settings.app_version,
        "healthy": True,
        "uptime_seconds": 0,
        "auth_type": auth.token_type,
        "user_id": auth.user_id,
    }
