from datetime import datetime
from typing import Optional
from enum import Enum
from sqlalchemy import Column, DateTime, func

from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Role(str, Enum):
    GOVERNMENT = "GOVERNMENT"
    CONTRACTOR = "CONTRACTOR"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, sa_column_kwargs={"unique": True})
    hashed_password: str
    role: Role = Field(default=Role.CONTRACTOR)
    identifier: Optional[str] = Field(default=None, index=True, sa_column_kwargs={"unique": True})
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            DateTime(timezone=False),
            server_default=func.now(),
            nullable=False,
        )
    )

    # relationships
    contractors: List["Contractor"] = Relationship(back_populates="owner")
