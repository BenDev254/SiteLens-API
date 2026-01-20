# app/api/v1/video_upload.py

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException,
    Form,
)
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional
import os
import shutil
import logging

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.project import Project
from app.models.assessment_result import AssessmentResult
from app.schemas.assessments import AssessmentResponse
from app.services.gemini_service import analyze_video
import json
from typing import Any

router = APIRouter(prefix="/safety", tags=["safety"])

logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads/videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)





def force_json_safe(value: Any):
    """
    Recursively convert ANY object into JSON-safe primitives.
    This is the nuclear option and guarantees DB safety.
    """
    try:
        json.dumps(value)
        return value
    except TypeError:
        pass

    if isinstance(value, dict):
        return {k: force_json_safe(v) for k, v in value.items()}

    if isinstance(value, list):
        return [force_json_safe(v) for v in value]

    if hasattr(value, "__dict__"):
        return force_json_safe(vars(value))

    return str(value)


def serialize_gemini_response(response) -> dict:
    """
    Final, DB-safe Gemini serializer.
    """

    # Best case: Gemini text output
    if hasattr(response, "text") and isinstance(response.text, str):
        return {"text": response.text}

    if hasattr(response, "output_text") and isinstance(response.output_text, str):
        return {"text": response.output_text}

    # Controlled extraction
    payload = {}

    if hasattr(response, "candidates"):
        payload["candidates"] = []
        for c in response.candidates:
            parts = []
            if hasattr(c, "content") and hasattr(c.content, "parts"):
                for p in c.content.parts:
                    if hasattr(p, "text"):
                        parts.append(p.text)
            payload["candidates"].append({"text": "\n".join(parts)})

    if hasattr(response, "usage_metadata"):
        payload["usage"] = {
            "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", None),
            "candidates_tokens": getattr(response.usage_metadata, "candidates_token_count", None),
            "total_tokens": getattr(response.usage_metadata, "total_token_count", None),
        }

    if not payload:
        payload["raw"] = str(response)

    # 🔒 GUARANTEE JSON SAFETY
    return force_json_safe(payload)


@router.post(
    "/projects/{project_id}/video/upload",
    response_model=AssessmentResponse,
)
async def assess_uploaded_video(
    project_id: int,
    video: UploadFile = File(...),  # REQUIRED → Upload button
    context_text: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    """
    Upload a construction site video and run AI safety analysis.
    """

    logger.info("Video upload started | project_id=%s", project_id)

    # Validate project
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a video file.",
        )

    # Save video to disk
    filename = f"{project_id}_{int(datetime.utcnow().timestamp())}_{video.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    logger.info("Video saved successfully | path=%s", file_path)

    # Read bytes for Gemini
    with open(file_path, "rb") as f:
        video_bytes = f.read()

    prompt = context_text or (
        "Analyze this construction site video for safety hazards, "
        "unsafe behavior, PPE violations, equipment risks, and environmental dangers."
    )

    # Gemini analysis
    logger.info("Sending video to Gemini | project_id=%s", project_id)

    gemini_raw_response = await analyze_video(
        project_id=project_id,
        video_bytes=video_bytes,
        prompt=prompt,
        mime_type=video.content_type,
    )

    logger.info("Gemini analysis completed | project_id=%s", project_id)

    # Serialize response BEFORE DB interaction
    gemini_response = serialize_gemini_response(gemini_raw_response)

    # Persist assessment
    assessment = AssessmentResult(
        project_id=project_id,
        score=100,
        notes=context_text or "Uploaded video safety assessment",
        image_path=file_path,
        gemini_response=gemini_response,
        created_at=datetime.utcnow(),
    )

    session.add(assessment)

    logger.info("Committing assessment to database | project_id=%s", project_id)

    await session.commit()
    await session.refresh(assessment)

    logger.info(
        "Video assessment pipeline completed | assessment_id=%s",
        assessment.id,
    )

    return {
        "assessment": assessment,
        "hazards": [],
    }
