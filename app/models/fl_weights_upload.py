from typing import Optional, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON


class FLWeightsUpload(SQLModel, table=True):
    __tablename__ = "fl_weights_upload"

    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="flexperiment.id")
    uploader_id: Optional[int] = Field(default=None, foreign_key="users.id")
    round: int
    weights: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    dataset_size: int = Field(default=0)
    storage_key: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
