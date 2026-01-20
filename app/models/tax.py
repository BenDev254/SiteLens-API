from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON, Column
from enum import Enum


class TaxStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class TaxSubmission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    reporter_id: Optional[int] = Field(default=None, foreign_key="users.id")
    reported_amount: float
    computed_amount: float
    variance: float
    status: TaxStatus = Field(default=TaxStatus.DRAFT)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    gemini_output: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))


class TaxAudit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="taxsubmission.id")
    auditor_id: Optional[int] = Field(default=None, foreign_key="users.id")
    notes: Optional[str] = None
    result: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
