from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime, date


class ResearchLogCreate(BaseModel):
    project_id: int
    action: str
    details: Optional[Dict[str, Any]] = None


class ResearchLogRead(BaseModel):
    id: int
    project_id: int
    user_id: Optional[int]
    action: str
    details: Optional[Dict[str, Any]]
    created_at: datetime


class ResearchExportRequest(BaseModel):
    project_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    format: Optional[str] = "csv"  # csv or json
