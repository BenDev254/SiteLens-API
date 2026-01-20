# app/api/v1/video_live.py

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Form,
)
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.project import Project
from app.models.assessment_result import AssessmentResult
from app.schemas.assessments import AssessmentResponse
from app.services.gemini_service import _call_gemini

router = APIRouter(prefix="/safety", tags=["safety"])


def serialize_gemini_response(response) -> dict:
    """
    Normalize Gemini response into JSON-safe structure
    """

    # Case 1: Already JSON-safe
    if isinstance(response, dict):
        return response

    # Case 2: Standard Gemini text output
    if hasattr(response, "text") and isinstance(response.text, str):
        return {"text": response.text}

    if hasattr(response, "output_text"):
        return {"text": response.output_text}

    # Case 3: Full GenerateContentResponse
    extracted = {}

    try:
        # Extract model version if present
        if hasattr(response, "model_version"):
            extracted["model_version"] = response.model_version

        # Extract candidates text safely
        if hasattr(response, "candidates"):
            extracted["candidates"] = []
            for c in response.candidates:
                if hasattr(c, "content") and hasattr(c.content, "parts"):
                    text_parts = []
                    for p in c.content.parts:
                        if hasattr(p, "text"):
                            text_parts.append(p.text)
                    extracted["candidates"].append(
                        {"text": "\n".join(text_parts)}
                    )

        # Extract token usage (safe primitives only)
        if hasattr(response, "usage_metadata"):
            extracted["usage"] = {
                "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", None),
                "candidates_tokens": getattr(response.usage_metadata, "candidates_token_count", None),
                "total_tokens": getattr(response.usage_metadata, "total_token_count", None),
            }

    except Exception as e:
        extracted["error"] = str(e)

    return extracted


@router.post(
    "/projects/{project_id}/video/live",
    response_model=AssessmentResponse,
)
async def assess_live_video_feed(
    project_id: int,
    live_feed_url: str = Form(...),
    context_text: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    """
    Analyze a live construction site video feed (RTSP / HLS / HTTP).
    """

    # Validate project
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    prompt = (
        f"Project ID: {project_id}\n"
        "You are monitoring a live construction site CCTV feed.\n\n"
        f"Live feed URL: {live_feed_url}\n\n"
        "Identify:\n"
        "- Safety hazards observable via CCTV\n"
        "- Unsafe behaviors and missing PPE\n"
        "- High-risk zones (edges, scaffolding, machinery)\n"
        "- Recommended alert rules and monitoring improvements\n\n"
        f"Additional context:\n{context_text or 'None'}"
    )

    # Call Gemini
    gemini_response = await _call_gemini(prompt)

    # Persist assessment
    assessment = AssessmentResult(
        project_id=project_id,
        score=100,
        notes=context_text or "Live video feed safety assessment",
        image_path=live_feed_url,
        gemini_response=serialize_gemini_response(gemini_response),
        created_at=datetime.utcnow(),
    )

    session.add(assessment)
    await session.commit()
    await session.refresh(assessment)

    return {
        "assessment": assessment,
        "hazards": [],
    }
