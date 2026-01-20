from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column


class AIConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    version: int = Field(default=1, nullable=False)
    config: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Optional["Project"] = Relationship(back_populates="ai_configs")


class AIConfigAudit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ai_config_id: int = Field(foreign_key="aiconfig.id")
    project_id: int = Field(foreign_key="project.id")
    previous_version: Optional[int] = None
    new_version: int = Field(nullable=False)
    change_reason: Optional[str] = None
    diff: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
