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
from app.models.project_document import ProjectDocument
from app.schemas.assessments import AssessmentResponse
from app.services.gemini_service import analyze_video
import json
from typing import Any

router = APIRouter(prefix="/safety", tags=["safety"])

logger = logging.getLogger(__name__)


UPLOAD_PROGRESS_CHUNK_SIZE = 5 * 1024 * 1024  


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
    video: UploadFile = File(...),
    context_text: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    logger.info(
        "Video upload started | project_id=%s | filename=%s | content_type=%s",
        project_id,
        video.filename,
        video.content_type,
    )

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not video.content_type or not video.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a video file.",
        )

    # ---------------------------------------------------
    # 1️⃣ STREAM READ WITH PROGRESS LOGGING
    # ---------------------------------------------------
    total_read = 0
    video_chunks: list[bytes] = []

    while True:
        chunk = await video.read(UPLOAD_PROGRESS_CHUNK_SIZE)
        if not chunk:
            break

        video_chunks.append(chunk)
        total_read += len(chunk)

        logger.info(
            "Video upload progress | project_id=%s | filename=%s | bytes_read=%s",
            project_id,
            video.filename,
            total_read,
        )

    if total_read == 0:
        raise HTTPException(status_code=400, detail="Empty video file")

    video_bytes = b"".join(video_chunks)

    logger.info(
        "Video upload completed | project_id=%s | filename=%s | total_bytes=%s",
        project_id,
        video.filename,
        total_read,
    )

    # ---------------------------------------------------
    # 2️⃣ STORE VIDEO IN DB
    # ---------------------------------------------------
    document = ProjectDocument(
        project_id=project_id,
        type="video",
        filename=video.filename,
        content=video_bytes,
        content_type=video.content_type,
        storage_key=f"project_{project_id}/videos/{video.filename}",
        created_at=datetime.utcnow(),
    )

    session.add(document)
    await session.commit()
    await session.refresh(document)

    logger.info(
        "Video persisted to DB | project_id=%s | document_id=%s | size_bytes=%s",
        project_id,
        document.id,
        len(video_bytes),
    )

    # ---------------------------------------------------
    # 3️⃣ GEMINI ANALYSIS
    # ---------------------------------------------------
    prompt = context_text or (
        "Analyze this construction site video for safety hazards, "
        "unsafe behavior, PPE violations, equipment risks, and environmental dangers."
    )

    logger.info(
        "Gemini analysis started | project_id=%s | document_id=%s",
        project_id,
        document.id,
    )

    gemini_raw_response = await analyze_video(
        project_id=project_id,
        video_bytes=document.content,
        prompt=prompt,
        mime_type=document.content_type,
    )

    logger.info(
        "Gemini analysis completed | project_id=%s | document_id=%s",
        project_id,
        document.id,
    )

    gemini_response = serialize_gemini_response(gemini_raw_response)

    # ---------------------------------------------------
    # 4️⃣ PERSIST ASSESSMENT
    # ---------------------------------------------------
    assessment = AssessmentResult(
        project_id=project_id,
        score=100,
        notes=context_text or "Uploaded video safety assessment",
        document_id=document.id,
        gemini_response=gemini_response,
        created_at=datetime.utcnow(),
    )

    session.add(assessment)
    await session.commit()
    await session.refresh(assessment)

    logger.info(
        "Video assessment pipeline completed | assessment_id=%s | document_id=%s",
        assessment.id,
        document.id,
    )

    return {
        "assessment": assessment,
        "hazards": [],
    }
