# app/api/v1/doc_assessment.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import os, shutil
from typing import Optional
import docx2txt
import PyPDF2

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.project import Project
from app.models.assessment_result import AssessmentResult
from app.schemas.assessments import AssessmentResponse
from app.services.gemini_service import _call_gemini  # We'll use your existing helper

router = APIRouter(prefix="/safety", tags=["safety"])

UPLOAD_DIR = "uploads/documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def serialize_gemini_response(response) -> dict:
    """
    Convert Gemini response to JSON-serializable dict
    """
    if isinstance(response, dict):
        return response
    if hasattr(response, "output_text"):
        return {"text": response.output_text}
    # fallback: convert __dict__ attributes
    result = {}
    for attr in dir(response):
        if attr.startswith("_"):
            continue
        try:
            value = getattr(response, attr)
            import json
            json.dumps(value)  # check if serializable
            result[attr] = value
        except Exception:
            result[attr] = str(value)
    return result


async def extract_text_from_file(file_path: str, content_type: str) -> str:
    """
    Extract text from PDF, DOCX, or fallback for unsupported files
    """
    if content_type == "application/pdf":
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text
    elif content_type in [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]:
        return docx2txt.process(file_path)
    elif content_type.startswith("image/"):
        # Images will be sent directly to Gemini (handled in service)
        return ""
    else:
        # Fallback: treat as binary -> string for Gemini
        with open(file_path, "rb") as f:
            return f.read().decode("utf-8", errors="ignore")


@router.post("/projects/{project_id}/upload", response_model=AssessmentResponse)
async def assess_document(
    project_id: int,
    document: UploadFile = File(...),
    context_text: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user)
):
    # Validate project
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save uploaded file
    filename = f"{project_id}_{int(datetime.utcnow().timestamp())}_{document.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(document.file, f)

    # Extract text if possible
    text_content = await extract_text_from_file(file_path, document.content_type)

    # Prepare Gemini prompt
    prompt = context_text or "Analyze this document for construction project safety, cost, and risks."
    if text_content:
        prompt += f"\n\nDocument content:\n{text_content}"

    # Call Gemini
    gemini_response = await _call_gemini(prompt)

    # Generate simple score (keep 100 if no hazards parsing implemented)
    score = 100

    # Save assessment
    assessment = AssessmentResult(
        project_id=project_id,
        score=score,
        notes=context_text or "Document analyzed by AI",
        image_path=file_path,  # we store file path in the existing column
        gemini_response=serialize_gemini_response(gemini_response),
        created_at=datetime.utcnow()
    )
    session.add(assessment)
    await session.commit()
    await session.refresh(assessment)

    return {
        "assessment": assessment,
        "hazards": []  # Currently no hazards parsing for generic documents
    }
