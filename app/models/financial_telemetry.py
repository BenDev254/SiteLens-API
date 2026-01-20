from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class FinancialTelemetry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    amount: float
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
