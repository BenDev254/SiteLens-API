from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class FLGlobalModel(SQLModel, table=True):
    __tablename__ = "fl_global_model"

    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="flexperiment.id", index=True)

    round: int
    weights: Dict[str, Any] = Field(sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
