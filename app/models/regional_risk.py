from typing import Optional
from sqlmodel import SQLModel, Field


class RegionalRisk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    region_name: str
    risk_score: float
    notes: Optional[str] = None
