from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from app.services.gemini_service import verify_compliance
from app.schemas.compliance import (
    ComplianceRequest,
    ComplianceResponse,
    TaxCalculateRequest,
    TaxCalculateResponse,
    TaxSubmitResponse,
    TaxValidateRequest,
    TaxHistoryResponse,
)
from app.core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.services.compliance_service import (
    calculate_tax,
    persist_submission,
    submit_tax,
    validate_submission,
    list_submissions,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.post("/verify", response_model=ComplianceResponse)
async def verify(payload: ComplianceRequest, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    res = await verify_compliance(payload.text, regulation_query=payload.regulation_query)
    return ComplianceResponse(verdict=res.get("verdict"), grounding=res.get("grounding"))


@router.post("/tax/calculate", response_model=TaxCalculateResponse)
async def tax_calculate(payload: TaxCalculateRequest, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    res = await calculate_tax(session, payload.project_id, payload.reported_amount, payload.revenues, payload.expenses, payload.tax_rate, payload.context_query)
    return TaxCalculateResponse(**res)


@router.post("/tax/submit/{project_id}", response_model=TaxSubmitResponse)
async def tax_submit(project_id: int, payload: TaxCalculateRequest, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    calc = await calculate_tax(session, payload.project_id, payload.reported_amount, payload.revenues, payload.expenses, payload.tax_rate, payload.context_query)
    sub = await persist_submission(session, project_id, user.id, payload.reported_amount, calc["computed_amount"], calc["variance"], gemini_output=calc.get("gemini_analysis"))
    sub = await submit_tax(session, sub.id, user.id, change_reason="user_submission")
    return TaxSubmitResponse(submission_id=sub.id, status=sub.status.value, submitted_at=sub.submitted_at)


@router.post("/tax/validate", response_model=dict)
async def tax_validate(payload: TaxValidateRequest, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    try:
        res = await validate_submission(session, payload.submission_id, payload.project_id, payload.reported_amount, payload.computed_amount, payload.context_query)
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/tax/history", response_model=TaxHistoryResponse)
async def tax_history(project_id: Optional[int] = None, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    items = await list_submissions(session, project_id)
    data = [
        {
            "id": i.id,
            "project_id": i.project_id,
            "reporter_id": i.reporter_id,
            "reported_amount": i.reported_amount,
            "computed_amount": i.computed_amount,
            "variance": i.variance,
            "status": i.status.value if hasattr(i.status, "value") else i.status,
            "created_at": i.created_at,
            "submitted_at": i.submitted_at,
        }
        for i in items
    ]
    return TaxHistoryResponse(items=data, total=len(data))
