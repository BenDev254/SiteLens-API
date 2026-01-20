from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tax import TaxSubmission, TaxAudit, TaxStatus
from app.services.gemini_service import _call_gemini, search_web


async def calculate_tax(session: AsyncSession, project_id: int, reported_amount: float, revenues: Optional[Dict[str, float]] = None, expenses: Optional[Dict[str, float]] = None, tax_rate: float = 0.2, context_query: Optional[str] = None) -> Dict[str, Any]:
    # Simple computation: computed_amount = tax_rate * (sum(revenues) - sum(expenses))
    rev_sum = sum(revenues.values()) if revenues else 0.0
    exp_sum = sum(expenses.values()) if expenses else 0.0
    taxable = max(rev_sum - exp_sum, 0.0)
    computed = taxable * tax_rate
    variance = reported_amount - computed

    # Grounding via Google Search if provided
    grounding = []
    if context_query:
        grounding = await search_web(context_query)

    # Ask Gemini to analyze cost variance and possible explanations
    prompt = (
        f"You are an expert tax auditor. For project {project_id} the reported tax is {reported_amount:.2f} and the computed tax is {computed:.2f} (based on revenues {rev_sum:.2f} and expenses {exp_sum:.2f}). "
        "Identify potential causes for variance, classify risk and suggest next steps. Provide a short summary and list of observations."
    )
    if grounding:
        prompt += "\n\nUse the following references: \n" + "\n".join([f"- {g['title']}: {g['link']}" for g in grounding])

    gemini_resp = await _call_gemini(prompt)

    # Do not persist here (calculation only). Return results and gemini analysis
    return {"project_id": project_id, "computed_amount": computed, "variance": variance, "gemini_analysis": {"raw": gemini_resp, "grounding": grounding}}


async def persist_submission(session: AsyncSession, project_id: int, reporter_id: Optional[int], reported_amount: float, computed_amount: float, variance: float, gemini_output: Optional[Dict[str, Any]] = None) -> TaxSubmission:
    sub = TaxSubmission(project_id=project_id, reporter_id=reporter_id, reported_amount=reported_amount, computed_amount=computed_amount, variance=variance, status=TaxStatus.PENDING, created_at=datetime.utcnow())
    if gemini_output:
        sub.gemini_output = gemini_output
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


async def submit_tax(session: AsyncSession, submission_id: int, submitter_id: int, change_reason: Optional[str] = None) -> TaxSubmission:
    sub = await session.get(TaxSubmission, submission_id)
    if not sub:
        raise ValueError("submission not found")
    sub.status = TaxStatus.SUBMITTED
    sub.submitted_at = datetime.utcnow()
    session.add(sub)
    await session.commit()

    # Create audit entry using Gemini to summarize and verify
    prompt = (
        f"You are an audit assistant. Summarize submission {submission_id} for project {sub.project_id}. "
        f"Reported: {sub.reported_amount:.2f}, Computed: {sub.computed_amount:.2f}, Variance: {sub.variance:.2f}. Provide verdict and suggested next steps."
    )
    gem_resp = await _call_gemini(prompt)

    audit = TaxAudit(submission_id=sub.id, auditor_id=None, notes=change_reason, result={"raw": gem_resp})
    session.add(audit)
    await session.commit()
    await session.refresh(audit)
    return sub


async def validate_submission(session: AsyncSession, submission_id: Optional[int] = None, project_id: Optional[int] = None, reported_amount: Optional[float] = None, computed_amount: Optional[float] = None, context_query: Optional[str] = None):
    # If submission_id provided, validate that record
    if submission_id:
        sub = await session.get(TaxSubmission, submission_id)
        if not sub:
            raise ValueError("submission not found")
        reported_amount = sub.reported_amount
        computed_amount = sub.computed_amount
        project_id = sub.project_id

    if reported_amount is None or computed_amount is None or project_id is None:
        raise ValueError("Missing required fields to validate")

    grounding = []
    if context_query:
        grounding = await search_web(context_query)

    prompt = (
        f"You are an expert auditor. Validate whether the reported tax {reported_amount:.2f} for project {project_id} matches the computed {computed_amount:.2f}. Identify discrepancies and suggest if submission should pass or be flagged."
    )
    if grounding:
        prompt += "\n\nReferences:\n" + "\n".join([f"- {g['title']}: {g['link']}" for g in grounding])

    gem_resp = await _call_gemini(prompt)

    # Persist audit
    audit = TaxAudit(submission_id=submission_id or 0, auditor_id=None, notes=None, result={"raw": gem_resp})
    session.add(audit)
    await session.commit()
    await session.refresh(audit)

    return {"submission_id": submission_id, "result": gem_resp, "grounding": grounding}


async def list_submissions(session: AsyncSession, project_id: Optional[int] = None):
    stmt = select(TaxSubmission)
    if project_id:
        stmt = stmt.where(TaxSubmission.project_id == project_id)
    result = await session.execute(stmt)
    items = result.scalars().all()
    return items
