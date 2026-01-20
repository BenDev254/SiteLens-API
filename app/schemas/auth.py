from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import Optional
from app.models.user import Role


class UserCreate(BaseModel):
    username: str
    password: str
    role: Role = Role.CONTRACTOR
    identifier: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: Role
    identifier: Optional[str]
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class TokenPayload(BaseModel):
    sub: str
    exp: int
    role: Optional[Role] = None
