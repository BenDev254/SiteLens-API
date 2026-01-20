from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Transcript(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    text: str
    source: Optional[str] = Field(default="live_ws")
    created_at: datetime = Field(default_factory=datetime.utcnow)
