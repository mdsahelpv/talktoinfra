from fastapi import Header, HTTPException, Depends
from src.config import settings


async def verify_api_key(x_api_key: str = Header(default="")) -> str:
    if not settings.enable_auth:
        return "anonymous"
    valid_keys = [k.strip() for k in settings.api_keys.split(",") if k.strip()]
    if not valid_keys:
        return "anonymous"
    if x_api_key in valid_keys:
        return x_api_key
    raise HTTPException(status_code=401, detail="Invalid API key")
