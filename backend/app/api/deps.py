import secrets
import uuid

import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.redis_client import get_redis
from app.schemas.user import CurrentUser


async def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session


async def get_redis_dep():
    return await get_redis()


async def get_arq_pool():
    """Return an ARQ Redis pool with enqueue_job support."""
    from arq.connections import create_pool, RedisSettings
    pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return pool


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> CurrentUser:
    """Require authenticated user. Accepts our app JWT or static API key (admin)."""
    token: str | None = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
    elif x_api_key:
        token = x_api_key

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Static API key → synthetic admin (for CLI / MCP usage)
    if settings.API_KEY and secrets.compare_digest(token.encode(), settings.API_KEY.encode()):
        return CurrentUser(
            id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            email="api-key@system",
            display_name="API Key",
            role="admin",
        )

    # App JWT
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return CurrentUser(
        id=uuid.UUID(payload["uid"]),
        email=payload["sub"],
        display_name=payload.get("name"),
        role=payload.get("role", "viewer"),
    )


async def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# Deprecated — kept for backward compat; use get_current_user instead
async def require_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> None:
    if not settings.REQUIRE_API_KEY:
        return
    provided_key: str | None = None
    if authorization and authorization.startswith("Bearer "):
        provided_key = authorization.removeprefix("Bearer ")
    elif x_api_key:
        provided_key = x_api_key
    if not provided_key or not settings.API_KEY:
        raise HTTPException(status_code=401, detail="API key required")
    if not secrets.compare_digest(provided_key.encode(), settings.API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")
