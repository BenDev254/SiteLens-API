from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from sqlalchemy import select, insert, update, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_document import ProjectDocument
from app.models.ai_config import AIConfig, AIConfigAudit
from app.models.contractor import Contractor
from app.models.enforcement_action import EnforcementAction
from app.services.auth_service import get_user_by_username


async def create_project(session: AsyncSession, contractor_id: int, name: str, description: Optional[str] = None) -> Project:
    # Validate that contractor exists
    contractor = await session.get(Contractor, contractor_id)
    if not contractor:
        raise ValueError(f"Contractor with id {contractor_id} not found")
    
    project = Project(contractor_id=contractor_id, name=name, description=description)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def list_projects(session: AsyncSession, q: Optional[str] = None) -> List[Project]:
    stmt = select(Project)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Project.name.ilike(like)) | (Project.description.ilike(like)))
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_project(session: AsyncSession, project_id: int) -> Optional[Project]:
    result = await session.execute(select(Project).where(Project.id == project_id))
    return result.scalars().first()


# Ownership helper: project -> contractor -> owner
async def check_ownership(session: AsyncSession, project: Project, user) -> bool:
    contractor = await session.get(Contractor, project.contractor_id)
    return contractor is not None and contractor.owner_id == user.id


def generate_presigned_url(storage_key: str, expires_seconds: int = 3600, purpose: str = "download") -> str:
    # Placeholder presigned URL generator. Replace with provider SDK (GCS/S3) in production.
    token = f"token-{int(datetime.utcnow().timestamp())}"
    url = f"https://storage.example.com/{storage_key}?token={token}&exp={expires_seconds}&purpose={purpose}"
    return url


async def create_document(session: AsyncSession, project_id: int, doc_type: str, filename: str, storage_key: str) -> ProjectDocument:
    doc = ProjectDocument(project_id=project_id, type=doc_type, filename=filename, storage_key=storage_key)
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def delete_document(session: AsyncSession, project_id: int, record_id: int) -> bool:
    result = await session.execute(select(ProjectDocument).where(ProjectDocument.id == record_id, ProjectDocument.project_id == project_id))
    doc = result.scalars().first()
    if not doc:
        return False
    await session.delete(doc)
    await session.commit()
    return True


async def get_signed_url_for_doc(session: AsyncSession, project_id: int, doc_type: str, filename: str, purpose: str = "download") -> Dict[str, Any]:
    # For uploads: create a storage_key and return presigned URL
    storage_key = f"projects/{project_id}/{doc_type}/{int(datetime.utcnow().timestamp())}-{filename}"
    url = generate_presigned_url(storage_key, purpose=purpose)
    return {"url": url, "storage_key": storage_key}


# AI config functions
async def get_latest_ai_config(session: AsyncSession, project_id: int) -> Optional[AIConfig]:
    stmt = select(AIConfig).where(AIConfig.project_id == project_id).order_by(AIConfig.version.desc()).limit(1)
    result = await session.execute(stmt)
    return result.scalars().first()


async def upsert_ai_config(session: AsyncSession, project_id: int, config: Dict[str, Any], change_reason: Optional[str] = None) -> AIConfig:
    latest = await get_latest_ai_config(session, project_id)
    new_version = 1 if not latest else latest.version + 1
    ai = AIConfig(project_id=project_id, version=new_version, config=config)
    session.add(ai)
    await session.commit()
    await session.refresh(ai)

    # create audit
    audit = AIConfigAudit(ai_config_id=ai.id, project_id=project_id, previous_version=(latest.version if latest else None), new_version=new_version, change_reason=change_reason, diff=config)
    session.add(audit)
    await session.commit()
    return ai


async def reset_ai_config(session: AsyncSession, project_id: int, change_reason: Optional[str] = "reset") -> AIConfig:
    default = {"model": "gemini-1.5-pro", "params": {}}
    return await upsert_ai_config(session, project_id, default, change_reason)


async def get_ai_config_audit(session: AsyncSession, project_id: int):
    stmt = select(AIConfigAudit).where(AIConfigAudit.project_id == project_id).order_by(AIConfigAudit.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


async def project_readiness(session: AsyncSession, project_id: int) -> Dict[str, Any]:
    # Simple heuristic: docs present, assessments present, no open enforcement actions
    docs_stmt = select(func.count()).select_from(ProjectDocument).where(ProjectDocument.project_id == project_id)
    assessments_stmt = select(func.count()).select_from(select(func.count()).select_from(Project).where(Project.id == project_id).subquery())
    # simplified
    doc_count = (await session.execute(docs_stmt)).scalar_one()
    enforcement_stmt = select(EnforcementAction).where(EnforcementAction.project_id == project_id, EnforcementAction.status != "RESOLVED")
    open_enfs = (await session.execute(enforcement_stmt)).scalars().all()

    score = 0
    details = {}
    if doc_count > 0:
        score += 40
        details["docs"] = True
    else:
        details["docs"] = False
    # check assessments
    assessment_stmt = select(func.count()).select_from(text("assessment_result")).where(text("project_id = :pid"))
    # keep simple; assume none
    details["assessments_present"] = False
    if len(open_enfs) == 0:
        score += 60
        details["no_open_enforcement"] = True
    else:
        details["no_open_enforcement"] = False

    return {"project_id": project_id, "readiness_score": score, "details": details}


async def get_project_ownership(session: AsyncSession, project_id: int) -> Optional[Dict[str, Any]]:
    """Get project ownership information including project_id, contractor_id, and owner details"""
    from app.models.user import User
    
    project = await get_project(session, project_id)
    if not project:
        return None
    
    contractor = await session.get(Contractor, project.contractor_id)
    owner = None
    if contractor:
        owner = await session.get(User, contractor.owner_id)
    
    return {
        "project_id": project.id,
        "project_name": project.name,
        "contractor_id": project.contractor_id,
        "contractor_name": contractor.name if contractor else None,
        "owner_id": contractor.owner_id if contractor else None,
        "owner_username": owner.username if owner else None,
        "owner_role": owner.role if owner else None,
    }


async def list_projects_with_ownership(session: AsyncSession, q: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all projects with ownership information"""
    from app.models.user import User
    
    projects = await list_projects(session, q=q)
    result = []
    
    for project in projects:
        contractor = await session.get(Contractor, project.contractor_id)
        owner = None
        if contractor:
            owner = await session.get(User, contractor.owner_id)
        
        result.append({
            "project_id": project.id,
            "project_name": project.name,
            "contractor_id": project.contractor_id,
            "contractor_name": contractor.name if contractor else None,
            "owner_id": contractor.owner_id if contractor else None,
            "owner_username": owner.username if owner else None,
            "owner_role": owner.role if owner else None,
        })
    
    return result


async def list_project_documents_with_ownership(session: AsyncSession, project_id: int) -> Optional[Dict[str, Any]]:
    """List all documents for a project including project owner_id"""
    project = await get_project(session, project_id)
    if not project:
        return None
    
    contractor = await session.get(Contractor, project.contractor_id)
    owner_id = contractor.owner_id if contractor else None
    
    stmt = select(ProjectDocument).where(ProjectDocument.project_id == project_id)
    result = await session.execute(stmt)
    documents = result.scalars().all()
    
    return {
        "project_id": project_id,
        "owner_id": owner_id,
        "documents": documents
    }

