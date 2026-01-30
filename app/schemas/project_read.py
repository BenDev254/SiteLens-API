from typing import Optional
from sqlmodel import SQLModel


class DashboardProjectStatsRead(SQLModel):
    totalAssessments:int
    criticalRisks:int
    averageSafetyScore: Optional[float]
    complianceRate: Optional[float] 
    financialRiskScore: Optional[float]
    laborForceIndex: Optional[float]
    flModelDrift: Optional[float]
    activeResearchNodes: Optional[int]


class DashboardProjectRead(SQLModel):
    id: int
    name: str
    description: Optional[str]
    location: Optional[str]
    status: str
    ownerType: Optional[str]
    stats: DashboardProjectStatsRead