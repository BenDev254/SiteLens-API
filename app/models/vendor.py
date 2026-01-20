from typing import Optional
from sqlmodel import SQLModel, Field, Relationship


class Vendor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contractor_id: Optional[int] = Field(default=None, foreign_key="contractor.id")
    contractor: Optional["Contractor"] = Relationship(back_populates="vendors")
