from pydantic import BaseModel
from datetime import datetime
import uuid


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    firebase_token: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CurrentUser(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    role: str
