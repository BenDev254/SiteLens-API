from typing import Optional, List
from pydantic import BaseModel
from datetime import date


class LaborCreate(BaseModel):
    project_id: int
    name: str
    role: Optional[str] = None
    hours: float = 0.0
    cost_per_hour: float = 0.0
    recorded_on: Optional[date] = None


class LaborRead(LaborCreate):
    id: int


class EquipmentCreate(BaseModel):
    project_id: int
    name: str
    quantity: int = 1
    cost_each: float = 0.0
    status: Optional[str] = "OPERATIONAL"


class EquipmentRead(EquipmentCreate):
    id: int


class LogisticsCreate(BaseModel):
    project_id: int
    type: str
    description: Optional[str] = None
    cost: float = 0.0
    scheduled_on: Optional[date] = None


class LogisticsRead(LogisticsCreate):
    id: int


class VendorCreate(BaseModel):
    name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contractor_id: Optional[int] = None


class VendorRead(VendorCreate):
    id: int


class ListResponse(BaseModel):
    items: List
    total: int
