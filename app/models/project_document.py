from typing import Optional
from datetime import datetime
from sqlmodel import LargeBinary, SQLModel, Field, Relationship


class ProjectDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    type: str
    filename: str

    content: bytes = Field(sa_column=LargeBinary)
    content_type: Optional[str]


    storage_key: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Optional["Project"] = Relationship(back_populates="documents")
