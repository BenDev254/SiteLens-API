from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from sqlalchemy import Column, Enum as SAEnum
from datetime import datetime


class ProjectStatus(str, Enum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contractor_id: int = Field(foreign_key="contractor.id")
    name: str
    description: Optional[str] = None
    status: ProjectStatus = Field(sa_column=Column(SAEnum(ProjectStatus), default=ProjectStatus.PLANNED))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    contractor: Optional["Contractor"] = Relationship(back_populates="projects")
    assessments: List["AssessmentResult"] = Relationship(back_populates="project")
    enforcement_actions: List["EnforcementAction"] = Relationship(back_populates="project")
    documents: List["ProjectDocument"] = Relationship(back_populates="project")
    ai_configs: List["AIConfig"] = Relationship(back_populates="project")
