from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


class TaxCalculateRequest(BaseModel):
    project_id: int
    reported_amount: float
    revenues: Optional[Dict[str, float]] = None
    expenses: Optional[Dict[str, float]] = None
    tax_rate: Optional[float] = 0.2
    context_query: Optional[str] = None


class TaxCalculateResponse(BaseModel):
    project_id: int
    computed_amount: float
    variance: float
    gemini_analysis: Optional[Dict[str, Any]] = None


class TaxSubmitResponse(BaseModel):
    submission_id: int
    status: str
    submitted_at: datetime


class TaxValidateRequest(BaseModel):
    submission_id: Optional[int] = None
    project_id: Optional[int] = None
    reported_amount: Optional[float] = None
    computed_amount: Optional[float] = None
    context_query: Optional[str] = None


class TaxHistoryItem(BaseModel):
    id: int
    project_id: int
    reporter_id: Optional[int]
    reported_amount: float
    computed_amount: float
    variance: float
    status: str
    created_at: datetime
    submitted_at: Optional[datetime]


class TaxHistoryResponse(BaseModel):
    items: List[TaxHistoryItem]
    total: int


class ComplianceRequest(BaseModel):
    text: str
    regulation_query: Optional[str] = None


class ComplianceResponse(BaseModel):
    verdict: Any
    grounding: Optional[Any] = None
