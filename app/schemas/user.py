from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime

from sqlmodel import SQLModel, Field
from enum import Enum
from sqlalchemy import Column, DateTime, func
from app.models.user import Role

# Input schema for creating users
class UserCreate(SQLModel):
    username: str
    password: str
    role: Role
    identifier: Optional[str] = None


# Output schema for reading users
class UserRead(SQLModel):
    id: int
    username: str
    role: Role
    identifier: Optional[str]
    created_at: datetime

