from typing import Optional
from sqlmodel import SQLModel, Field


class Professional(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    title: Optional[str] = None
    contractor_id: Optional[int] = Field(default=None, foreign_key="contractor.id")
