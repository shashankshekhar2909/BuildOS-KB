from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.api.deps import get_db, get_current_user
from app.auth import verify_firebase_token, create_access_token
from app.config import settings
from app.models.user import User
from app.schemas.user import LoginRequest, LoginResponse, UserOut, CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        claims = await verify_firebase_token(body.firebase_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {e}")

    email: str = claims.get("email", "").lower()
    display_name: str | None = claims.get("name")
    firebase_uid: str = claims.get("uid", claims.get("sub", ""))

    if not email:
        raise HTTPException(status_code=401, detail="Token missing email claim")

    # Check allowed list (if configured)
    allowed = settings.allowed_emails_list
    if allowed and email not in allowed:
        raise HTTPException(status_code=403, detail="Access not granted. Contact admin.")

    # Determine role
    role = "admin" if email in settings.admin_emails_list else "viewer"

    # Upsert user in DB
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=uuid.uuid4(),
            email=email,
            display_name=display_name,
            firebase_uid=firebase_uid,
            role=role,
        )
        db.add(user)
    else:
        # Sync display name and firebase_uid; preserve manually-assigned role unless in admin list
        user.display_name = display_name
        user.firebase_uid = firebase_uid
        if email in settings.admin_emails_list:
            user.role = "admin"
        role = user.role

    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        email=user.email,
        user_id=str(user.id),
        role=user.role,
        display_name=user.display_name,
    )

    return LoginResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.email == current_user.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)
