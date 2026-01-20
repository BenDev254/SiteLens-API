from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from sqlalchemy import Column, JSON


class AssessmentHazard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    assessment_id: int = Field(foreign_key="assessmentresult.id")
    hazard_type: str
    location: str
    risk_level: str
    recommendations: List[str] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    assessment: Optional["AssessmentResult"] = Relationship(back_populates="hazards")
