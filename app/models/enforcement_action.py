from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from sqlalchemy import Column, Enum as SAEnum


class EnforcementStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class EnforcementAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    description: str
    status: EnforcementStatus = Field(sa_column=Column(SAEnum(EnforcementStatus), default=EnforcementStatus.OPEN))

    project: Optional["Project"] = Relationship(back_populates="enforcement_actions")
