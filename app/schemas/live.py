from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class TelemetryCreate(BaseModel):
    project_id: int
    metric: str
    value: float
    tags: Optional[Dict[str, Any]] = None


class TelemetryRead(TelemetryCreate):
    id: int
    recorded_at: datetime


class AlertCreate(BaseModel):
    project_id: int
    alert_type: str
    severity: str
    message: str
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="alert_metadata")


class AlertRead(AlertCreate):
    id: int
    status: str
    created_at: datetime
    acknowledged_by: Optional[int]
    acknowledged_at: Optional[datetime]

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class AlertAckRequest(BaseModel):
    pass


class LiveConfigRead(BaseModel):
    project_id: int
    config: Optional[Dict[str, Any]]
    updated_at: datetime


class LiveConfigUpdate(BaseModel):
    config: Dict[str, Any]
