from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session
from sqlalchemy import func, select

from app.core.database import get_session
from app.models.assessment_result import AssessmentResult
from app.models.contractor import Contractor
from app.models.fl_experiment import FLExperiment
from app.models.labor import Labor
from app.models.project import Project, ProjectStatus
from app.models.project_document import ProjectDocument
from app.models.tax import TaxStatus, TaxSubmission
from app.schemas.project_read import DashboardProjectStatsRead, DashboardProjectRead
from app.services.project_service import (
    create_project,
    list_projects,
    get_project,
    get_signed_url_for_doc,
    create_document,
    delete_document,
    get_latest_ai_config,
    upsert_ai_config,
    reset_ai_config,
    get_ai_config_audit,
    project_readiness,
    check_ownership,
    get_project_ownership,
    list_projects_with_ownership,
    list_project_documents_with_ownership,
)
from app.schemas.domain import (
    ProjectCreate,
    ProjectRead,
    DocumentCreate,
    DocumentRead,
    ProjectDocumentsWithOwnershipRead,
)
from app.schemas.project_read import DashboardProjectRead
from app.core.security import get_current_user
from app.models.user import Role
from app.services.project_stats import compute_stats
from app.services.project_service import fetch_project

router = APIRouter(prefix="/projects", tags=["projects"]) 


@router.get("", response_model=List[ProjectRead])
async def get_projects(q: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    projects = await list_projects(session, q=q)  # the service function
    return [ProjectRead(**p.model_dump()) for p in projects]



@router.post("/create", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project_endpoint(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    """
    Create a project under the contractor associated with the current user.
    """
    # Fetch the contractor linked to this user
    contractor = await session.scalar(
        select(Contractor).where(Contractor.owner_id == user.id)
    )
    if not contractor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No contractor associated with user {user.id}"
        )

    project = await create_project(
        session,
        contractor_id=contractor.id,
        name=payload.name,
        description=payload.description
    )
    return ProjectRead(**project.model_dump())



@router.get("/search", response_model=List[ProjectRead])
async def search_projects(q: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    projects = await list_projects(session, q=q)
    return [ProjectRead(**p.model_dump()) for p in projects]


@router.get("/ownership/all")
async def get_all_projects_ownership(q: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    """Get all projects with ownership information (project_id, owner_id, owner_username, etc)"""
    return await list_projects_with_ownership(session, q=q)


@router.get("/{project_id}/ownership")
async def get_project_ownership_endpoint(project_id: int, session: AsyncSession = Depends(get_session)):
    """Get ownership information for a specific project"""
    ownership = await get_project_ownership(session, project_id)
    if not ownership:
        raise HTTPException(status_code=404, detail="Project not found")
    return ownership


@router.get("/{project_id}/documents-with-ownership", response_model=ProjectDocumentsWithOwnershipRead)
async def get_project_documents_with_ownership(project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    """Get all documents associated with a project, including project owner information"""
    data = await list_project_documents_with_ownership(session, project_id)
    if not data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Optional ownership check for contractors
    if user.role != Role.GOVERNMENT:
        project = await get_project(session, project_id)
        is_owner = await check_ownership(session, project, user)
        if not is_owner:
            raise HTTPException(status_code=403, detail="Not owner")
            
    return data


@router.get("/{project_id}/readiness")
async def readiness(project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # ownership check: government role can view any, contractors can only view their own
    if user.role != Role.GOVERNMENT:
        is_owner = await check_ownership(session, project, user)
        if not is_owner:
            raise HTTPException(status_code=403, detail="Not owner")
    return await project_readiness(session, project_id)


@router.get("/{project_id}/docs/{type}/signed-url")
async def get_signed_url(project_id: int, type: str, filename: str, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # ownership check: government role can view any, contractors can only view their own
    if user.role != Role.GOVERNMENT:
        is_owner = await check_ownership(session, project, user)
        if not is_owner:
            raise HTTPException(status_code=403, detail="Not owner")
    info = await get_signed_url_for_doc(session, project_id, type, filename, purpose="upload")
    return info



@router.post("/{project_id}/docs", response_model=DocumentRead)
async def create_doc(
    project_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user)
):
    project = await fetch_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if user.role != Role.GOVERNMENT:
        is_owner = await check_ownership(session, project, user)
        if not is_owner:
            raise HTTPException(status_code=403, detail="Not owner")

    contents = await file.read()

    doc = await create_document(
        session=session,
        project_id=project_id,
        doc_type=doc_type,
        filename=file.filename,
        content=contents,
        content_type=file.content_type
    )
    return DocumentRead.from_orm(doc)


@router.delete("/{project_id}/docs/{record_id}")
async def delete_doc(project_id: int, record_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if user.role != Role.GOVERNMENT:
        is_owner = await check_ownership(session, project, user)
        if not is_owner:
            raise HTTPException(status_code=403, detail="Not owner")
    ok = await delete_document(session, project_id, record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}


@router.get("/docs", response_model=List[DocumentRead])
async def list_my_documents(
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    """
    Return all documents accessible to the logged-in user. 
    - Government users see all documents
    - Non-government users see documents only for projects they own. 
    """

    if user.role == Role.GOVERNMENT:
        # Government: fetch all documents 
        result = await session.execute(select(ProjectDocument))
        docs = result.scalars().all()
    else:
        #Non-government: fetch only documents for projects they own 
        result = await session.execute(
            select(ProjectDocument)
            .join(Project, ProjectDocument.project_id == Project.id)
            .where(Project.contractor_id ==user.id)
        )
        docs = result.scalars().all()

    # Return using the Pyndatic schema 
    return [DocumentRead.from_orm(doc) for doc in docs]





@router.get("/{project_id}/ai-config")
async def get_ai_config(project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    ai = await get_latest_ai_config(session, project_id)
    return ai or {"message": "no config"}


@router.put("/{project_id}/ai-config")
async def put_ai_config(project_id: int, payload: dict, reason: str = "update", session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    ai = await upsert_ai_config(session, project_id, payload, change_reason=reason)
    return ai


@router.post("/{project_id}/ai-config/reset")
async def reset_ai_config_endpoint(project_id: int, reason: str = "reset", session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    ai = await reset_ai_config(session, project_id, change_reason=reason)
    return ai


@router.get("/{project_id}/ai-config/audit")
async def ai_config_audit(project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return await get_ai_config_audit(session, project_id)


@router.get("/{project_id}", response_model=DashboardProjectRead)
async def get_dashboard_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await session.execute(
        select(AssessmentResult).where(
            AssessmentResult.project_id == project_id
        )
    )
    assessments = result.scalars().all()

    stats = compute_stats(assessments)

    return DashboardProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        location="Upper Hill, Nairobi",       
        status=project.status.value.lower(),
        ownerType="PRIVATE",                  
        stats=DashboardProjectStatsRead(
            totalAssessments=stats["totalAssessments"],
            criticalRisks=stats["criticalRisks"],
            averageSafetyScore=stats["averageSafetyScore"],
            complianceRate=stats["complianceRate"],
            financialRiskScore=12,
            laborForceIndex=85,
            flModelDrift=0.02,
            activeResearchNodes=3,
        ),
    )




@router.get("/admin/dashboard")
async def admin_projects_dashboard(
    session: AsyncSession = Depends(get_session),
):
    """
    System-level metrics for admin dashboard. This is separate from the /projects/{id} endpoint which is more project-focused.
    """

    #----Projects----#
    total_projects = await session.scalar(
        select(func.count(Project.id))
    ) or 1 # avoid division by zero

    active_projects = await session.scalar(
        select(func.count(Project.id))
        .where(Project.status == ProjectStatus.ACTIVE)
    ) or 0 

    #----Labor----#
    total_labor_active = await session.scalar(
        select(func.count(Labor.id))
        .join(Project, Labor.project_id == Project.id)
        .where(Project.status == ProjectStatus.ACTIVE)
    ) or 0

    labor_force_index = (
        total_labor_active / active_projects
        if active_projects > 0
        else 0.0
    )


    #----FL Experiments----#
    total_fl_experiments = await session.scalar(
        select(func.count(FLExperiment.id))
    ) or 0

    fl_model_drift = total_fl_experiments / total_projects 


    #----Tax Risk----#
    total_tax_submissions = await session.scalar(
        select(func.count(TaxSubmission.id))
    ) or 0

    risky_tax_submissions = await session.scalar(
        select(func.count(TaxSubmission.id))
        .where(TaxSubmission.status != TaxStatus.VALIDATED)
    ) or 0

    financial_risk_score = (
        risky_tax_submissions / total_tax_submissions
        if total_tax_submissions > 0
        else 0.0
    )


    #----Response----#
    return {
        "projects": {
            "total": total_projects,
            "active": active_projects,
        },
        "laborForceIndex": round(labor_force_index, 2),
        "flModelDrift": round(fl_model_drift, 2),
        "financialRiskScore": round(financial_risk_score, 2),
    }



