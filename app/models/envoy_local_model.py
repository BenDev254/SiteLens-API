from typing import Any, Dict, Optional
from datetime import datetime
from sqlalchemy import Column
from sqlmodel import JSON, SQLModel, Field


class EnvoyLocalModel(SQLModel, table=True):
    __tablename__ = "envoy_local_model"

    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="flexperiment.id")
    participant_id: int = Field(foreign_key="fl_participant.id")
    round: int = 0
    weights: Optional[Dict[str, Any]] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

