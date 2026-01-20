from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Policy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: Optional[str] = None
    archived: bool = Field(default=False)
    archived_at: Optional[datetime] = None
    archived_by: Optional[int] = Field(default=None, foreign_key="users.id")
