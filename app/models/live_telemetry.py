from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON, Column


class LiveTelemetry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    metric: str
    value: float
    tags: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
