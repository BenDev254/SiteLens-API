from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Contractor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    owner_id: int = Field(foreign_key="users.id")

    owner: Optional["User"] = Relationship(back_populates="contractors")
    projects: List["Project"] = Relationship(back_populates="contractor")
    vendors: List["Vendor"] = Relationship(back_populates="contractor")
