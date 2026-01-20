from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import date


class Logistics(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    type: str
    description: Optional[str] = None
    cost: float = 0.0
    scheduled_on: Optional[date] = None
