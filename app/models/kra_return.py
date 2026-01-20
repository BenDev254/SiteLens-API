from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date


class KRAReturn(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    metric_name: str
    value: float
    period_start: Optional[date] = None
    period_end: Optional[date] = None
