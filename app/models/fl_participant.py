from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class FLParticipant(SQLModel, table=True):
    __tablename__ = "fl_participant"

    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="flexperiment.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: Optional[datetime] = None
    status: str = Field(default="ACTIVE")
