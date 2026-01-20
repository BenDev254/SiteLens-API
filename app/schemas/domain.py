from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict
from app.models.project import ProjectStatus
from app.models.user import Role


class ContractorCreate(BaseModel):
    name: str
    owner_id: int


class ContractorRead(BaseModel):
    id: int
    name: str
    owner_id: int


class ProjectCreate(BaseModel):
    contractor_id: int
    name: str
    description: Optional[str] = None


class ProjectRead(BaseModel):
    id: int
    contractor_id: int
    name: str
    description: Optional[str]
    status: ProjectStatus


class ProfessionalCreate(BaseModel):
    name: str
    title: Optional[str] = None
    contractor_id: Optional[int] = None


class ProfessionalRead(BaseModel):
    id: int
    name: str
    title: Optional[str]
    contractor_id: Optional[int]


class EnforcementActionCreate(BaseModel):
    project_id: int
    description: str


class EnforcementActionRead(BaseModel):
    id: int
    project_id: int
    description: str
    status: str


class AssessmentResultCreate(BaseModel):
    project_id: int
    score: float
    notes: Optional[str] = None


class AssessmentResultRead(BaseModel):
    id: int
    project_id: int
    score: float
    notes: Optional[str]


class KRAReturnCreate(BaseModel):
    project_id: int
    metric_name: str
    value: float
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class KRAReturnRead(BaseModel):
    id: int
    project_id: int
    metric_name: str
    value: float
    period_start: Optional[date]
    period_end: Optional[date]


class FinancialTelemetryCreate(BaseModel):
    project_id: int
    amount: float


class FinancialTelemetryRead(BaseModel):
    id: int
    project_id: int
    amount: float
    recorded_at: datetime


class RegionalRiskCreate(BaseModel):
    region_name: str
    risk_score: float


class RegionalRiskRead(BaseModel):
    id: int
    region_name: str
    risk_score: float
    notes: Optional[str]


class FLExperimentCreate(BaseModel):
    name: str
    params: Optional[Dict[str, Any]] = None


class FLExperimentRead(BaseModel):
    id: int
    name: str
    params: Optional[Dict[str, Any]]
    results: Optional[Dict[str, Any]]

class DocumentCreate(BaseModel):
    doc_type: str
    filename: str
    storage_key: str


class DocumentRead(BaseModel):


    id: int


    project_id: int


    type: str


    filename: str


    storage_key: str


    created_at: datetime


    


    model_config = ConfigDict(from_attributes=True)








class ProjectDocumentWithOwner(DocumentRead):


    owner_id: Optional[int]








class ProjectDocumentsWithOwnershipRead(BaseModel):


    project_id: int


    owner_id: Optional[int]


    documents: List[DocumentRead]
