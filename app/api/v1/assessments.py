from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.core.database import get_session
from app.core.security import get_current_user
from app.services.gemini_service import analyze_assessment, archive_assessment, log_trend
from app.schemas.assessments import AnalyzeRequest, AnalyzeResponse, ArchiveRequest, TrendLogRequest

router = APIRouter(prefix="/assessments", tags=["assessments"]) 



@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest,
                  session: AsyncSession = Depends(get_session),
                  user=Depends(get_current_user)):
    resp = await analyze_assessment(payload.texts, context_query=payload.context_query)
    return AnalyzeResponse(
        response=resp.get("response"),
        grounding=resp.get("grounding")
    )



@router.post("/archive")
async def archive(payload: ArchiveRequest, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    res = await archive_assessment(payload.assessment_id, notes=payload.notes)
    return res


@router.post("/trends/log")
async def trends_log(payload: TrendLogRequest, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    res = await log_trend(payload.project_id, payload.metric, payload.value, timestamp=payload.timestamp)
    return res
