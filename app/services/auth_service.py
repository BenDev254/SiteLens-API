from datetime import datetime, timedelta
from typing import Optional
import hashlib

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User

pwd_context = CryptContext(
    schemes=["argon2"], 
    deprecated="auto",
)

JWT_ALGORITHM = "HS256"
JWT_SECRET = getattr(settings, "SECRET_KEY", None) or "CHANGE_ME"
ACCESS_TOKEN_EXPIRE_MINUTES = int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60))


def get_password_hash(password: str) -> str:
    """Hash password using argon2."""
    if not isinstance(password, str):
        password = str(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password with argon2."""
    if not isinstance(plain_password, str):
        plain_password = str(plain_password)
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, Exception):
        # Handle any argon2 errors
        return False


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    q = await session.execute(select(User).where(User.username == username))
    return q.scalars().first()


async def create_user(session: AsyncSession, username: str, password: str, role, identifier: Optional[str] = None) -> User:
    hashed = get_password_hash(password)
    user = User(username=username, hashed_password=hashed, role=role, identifier=identifier)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, username: str, password: str) -> Optional[User]:
    user = await get_user_by_username(session, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(subject: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.utcnow()
    exp = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": str(subject), "exp": int(exp.timestamp()), "role": role}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise
    except jwt.PyJWTError:
        raise
