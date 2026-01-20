from typing import Optional
from sqlmodel import SQLModel, Field
from enum import Enum
from sqlalchemy import Column, Enum as SAEnum


class EquipmentStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    RETIRED = "RETIRED"


class Equipment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    name: str
    quantity: int = 1
    cost_each: float = 0.0
    status: EquipmentStatus = Field(sa_column=Column(SAEnum(EquipmentStatus), default=EquipmentStatus.OPERATIONAL))
