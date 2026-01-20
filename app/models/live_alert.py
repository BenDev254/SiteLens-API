from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON, Column


class AlertStatus(str):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class LiveAlert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    alert_type: str
    severity: str
    message: str
    status: str = Field(default=AlertStatus.OPEN)
    acknowledged_by: Optional[int] = Field(default=None, foreign_key="users.id")
    acknowledged_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    alert_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
