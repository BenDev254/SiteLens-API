from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from app.schemas.auth import UserCreate, UserResponse, Token
from app.services.auth_service import create_user, authenticate_user, create_access_token
from app.core.database import get_session
from app.models.user import Role

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(
        text("SELECT 1 FROM users WHERE username = :u"), {"u": payload.username}
    )
    if existing.first() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    user = await create_user(session, payload.username, payload.password, payload.role, payload.identifier)
    return UserResponse.from_orm(user)


@router.post("/token", response_model=Token)
async def token(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=60)
    token = create_access_token(subject=user.username, role=user.role.value, expires_delta=access_token_expires)
    return Token(access_token=token, expires_in=int(access_token_expires.total_seconds()))



@router.post("/reset-database", status_code=204)
async def reset_database(
    session: AsyncSession = Depends(get_session),
    
):
    """
    ⚠️ Deletes ALL rows from ALL SQLModel tables.
    Schema remains intact.
    """

    try:
        async with session.begin():
            for table in reversed(SQLModel.metadata.sorted_tables):
                await session.execute(delete(table))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
