from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class Contractor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    headquarters: Optional[str] = None

    owner_id: int = Field(foreign_key="users.id")  # links to User
    owner: Optional["User"] = Relationship(back_populates="contractors")

    projects: List["Project"] = Relationship(back_populates="contractor")
    vendors: List["Vendor"] = Relationship(back_populates="contractor")
    
