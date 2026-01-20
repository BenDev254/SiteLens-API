from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field


class Labor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    name: str
    role: Optional[str] = None
    hours: float = 0.0
    cost_per_hour: float = 0.0
    recorded_on: Optional[date] = None
