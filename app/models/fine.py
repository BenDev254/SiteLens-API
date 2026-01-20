from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Fine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    amount: float
    issued_by: Optional[int] = Field(default=None, foreign_key="users.id")
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="OPEN")
    notes: Optional[str] = None
