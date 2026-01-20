from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.core.database import get_session
from app.core.security import get_current_user
from app.services.research_service import log_interaction, list_history, export_history
from app.schemas.research import ResearchLogCreate, ResearchLogRead, ResearchExportRequest
from app.services.project_service import get_project, check_ownership

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/log", response_model=ResearchLogRead)
async def post_log(payload: ResearchLogCreate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user) and user.role != 'GOVERNMENT':
        raise HTTPException(status_code=403, detail="Not owner")
    rec = await log_interaction(session, payload.project_id, getattr(user, 'id', None), payload.action, payload.details)
    return ResearchLogRead(**rec.model_dump())


@router.get("/history", response_model=list)
async def get_history(project_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    # if project-scoped, enforce ownership
    if project_id:
        project = await get_project(session, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not await check_ownership(session, project, user) and user.role != 'GOVERNMENT':
            raise HTTPException(status_code=403, detail="Not owner")
    items = await list_history(session, project_id=project_id, start=start_date, end=end_date)
    return [ResearchLogRead(**i.model_dump()) for i in items]


@router.post("/export")
async def export(payload: ResearchExportRequest, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    # ownership enforcement if project specified
    if payload.project_id:
        project = await get_project(session, payload.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not await check_ownership(session, project, user) and user.role != 'GOVERNMENT':
            raise HTTPException(status_code=403, detail="Not owner")

    data = await export_history(session, project_id=payload.project_id, start=payload.start_date, end=payload.end_date, fmt=payload.format)

    if payload.format == "json":
        return StreamingResponse(io.BytesIO(data), media_type="application/json", headers={"Content-Disposition": "attachment; filename=research_export.json"})

    return StreamingResponse(io.BytesIO(data), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=research_export.csv"})
