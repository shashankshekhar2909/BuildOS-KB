"""Firebase token verification + JWT issuance."""
import asyncio
from datetime import datetime, timedelta
from functools import partial

import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import settings


def _verify_firebase_token_sync(token: str) -> dict:
    return id_token.verify_firebase_token(
        token,
        google_requests.Request(),
        audience=settings.FIREBASE_PROJECT_ID,
    )


async def verify_firebase_token(token: str) -> dict:
    """Verify Firebase ID token, return decoded claims. Runs sync Google cert fetch in thread."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_verify_firebase_token_sync, token))


def create_access_token(email: str, user_id: str, role: str, display_name: str | None = None) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": email,
        "uid": user_id,
        "role": role,
        "name": display_name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
