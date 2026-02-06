from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class FLExperiment(SQLModel, table=True):
    __tablename__ = "flexperiment"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

    params: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON)
    )
    results: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))

    participant_threshold: int = Field(default=3)
    current_round: int = Field(default=0)
    status: str = Field(default="CREATED")  

    created_at: datetime = Field(default_factory=datetime.utcnow)
