from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import os, shutil, re

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.project import Project
from app.models.assessment_result import AssessmentResult
from app.models.assessment_hazard import AssessmentHazard
from app.schemas.assessments import AssessmentResponse
from app.services.gemini_service import analyze_image, analyze_assessment

router = APIRouter(prefix="/safety", tags=["safety"])

UPLOAD_DIR = "uploads/images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def parse_gemini_hazards(text: str):
    hazards = []
    # Split by numbered hazards
    hazard_blocks = re.split(r"\n\*\*\d+\.\s+", text)
    for block in hazard_blocks[1:]:
        title_match = re.match(r"(.*?)(\n|$)", block)
        hazard_type = title_match.group(1).strip() if title_match else "Unknown Hazard"
        recs = re.findall(r"\*{1,2}\s*(.+?)(?:\n|$)", block)
        hazards.append({
            "hazard_type": hazard_type,
            "location": "",
            "risk_level": "",
            "recommendations": recs
        })
    return hazards

def serialize_gemini_response(response: dict) -> dict:
    serializable = {}
    for key, value in response.items():
        serializable[key] = str(value) if hasattr(value, "__dict__") else value
    return serializable

@router.post("/projects/{project_id}/image-assessment", response_model=AssessmentResponse)
async def assess_project_image(
    project_id: int,
    image: UploadFile = File(...),
    context_text: str = None,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user)
):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save uploaded image
    filename = f"{project_id}_{int(datetime.utcnow().timestamp())}_{image.filename}"
    image_path = os.path.join(UPLOAD_DIR, filename)
    with open(image_path, "wb") as f:
        shutil.copyfileobj(image.file, f)
    image_bytes = open(image_path, "rb").read()

    # Use user-provided context if present; otherwise default prompt
    vision_prompt = context_text if context_text else (
        "Analyze this construction site image. "
        "Identify safety hazards, locations, risk levels, and recommendations."
    )

    # Gemini analysis
    vision_result = await analyze_image(image_bytes, vision_prompt)
    vision_text = vision_result.get("text", "")

    # Extract structured hazards from Gemini response
    hazards = parse_gemini_hazards(vision_text)

    # Generate assessment notes and score
    analysis = await analyze_assessment(
        texts=[f"{h['hazard_type']} at {h['location']} ({h['risk_level']})" for h in hazards] or ["No hazards detected"],
        context_query="construction safety risk mitigation best practices"
    )

    score = max(0.0, 100.0 - len(hazards) * 15)

    # Save assessment record regardless of hazards
    assessment = AssessmentResult(
        project_id=project_id,
        score=score,
        notes=context_text or analysis["response"]["text"],
        image_path=image_path,
        gemini_response=serialize_gemini_response(vision_result),
        created_at=datetime.utcnow()
    )
    session.add(assessment)
    await session.commit()
    await session.refresh(assessment)

    # Save hazards
    for h in hazards:
        session.add(
            AssessmentHazard(
                assessment_id=assessment.id,
                hazard_type=h["hazard_type"],
                location=h["location"],
                risk_level=h["risk_level"],
                recommendations=h["recommendations"],
            )
        )
    await session.commit()

    return {
        "assessment": assessment,
        "hazards": hazards,
    }
