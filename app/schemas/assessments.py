from typing import List, Optional, Any, Dict
from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    texts: List[str]
    context_query: Optional[str] = None


class AnalyzeResponse(BaseModel):
    response: Any
    grounding: Optional[List[dict]] = None


class ArchiveRequest(BaseModel):
    assessment_id: int
    notes: Optional[str] = None


class TrendLogRequest(BaseModel):
    project_id: int
    metric: str
    value: float
    timestamp: Optional[str] = None


class HazardSchema(BaseModel):
    hazard_type: str
    location: str
    risk_level: str
    recommendations: List[str]


class AssessmentCreate(BaseModel):
    project_id: int


class AssessmentRead(BaseModel):
    id: int
    project_id: int
    score: float
    notes: Optional[str]
    image_path: Optional[str]
    gemini_response: Optional[Dict]


class AssessmentResponse(BaseModel):
    assessment: AssessmentRead
    hazards: List[HazardSchema]
