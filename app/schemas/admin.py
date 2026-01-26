from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr
from datetime import datetime


class FineCreate(BaseModel):
    project_id: Optional[int]
    amount: float
    notes: Optional[str] = None


class FineRead(BaseModel):
    id: int
    project_id: Optional[int]
    amount: float
    issued_by: Optional[int]
    issued_at: datetime
    status: str
    notes: Optional[str]


class PolicyArchiveRequest(BaseModel):
    policy_id: int
    reason: Optional[str] = None


class AdminAIConfigRead(BaseModel):
    id: int
    config: Optional[Dict[str, Any]]
    updated_at: datetime
    updated_by: Optional[int]


class AdminAIConfigUpdate(BaseModel):
    config: Dict[str, Any]


class RevenueStats(BaseModel):
    total_revenue: float
    total_fines: float
    total_projects: int
    avg_revenue_per_project: Optional[float]


class AuditRecord(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    details: Optional[Dict[str, Any]]
    created_at: datetime


class ContractorRead(BaseModel):
    id: int
    name: str
    headquarters: Optional[str] = None
    email: Optional[str] = None      
    identifier: Optional[str] = None  

    class Config:
        from_attributes = True

class ProfessionalRead(BaseModel):
    id: int
    name: str
    title: Optional[str] = None
    contractor_id: int
    email: Optional[str] = None  

    class Config:
        from_attributes = True



class ContractorCreate(BaseModel):
    name: str
    headquarters: Optional[str] = None
    email: Optional[str] = None 

class ProfessionalCreate(BaseModel):
    name: str
    title: Optional[str] = None
    contractor_id: int
    email: Optional[str] = None
