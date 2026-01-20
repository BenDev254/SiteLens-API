from typing import Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_result import AssessmentResult
from app.models.assessment_hazard import AssessmentHazard
from app.services.fl_service import get_global_model, upload_weights


RISK_MAP = {
    "LOW": 0.2,
    "MEDIUM": 0.6,
    "HIGH": 1.0
}


def extract_features(ar: AssessmentResult) -> Dict[str, float]:
    gem = ar.gemini_response or {}

    return {
        "safety": ar.score,
        "compliance": gem.get("compliance_score", 0.0),
        "structural": gem.get("structural_score", 0.0),
        "financial": gem.get("financial_score", 0.0),
    }


def extract_hazard_signal(hazards: List[AssessmentHazard]) -> float:
    if not hazards:
        return 0.0

    return sum(RISK_MAP.get(h.risk_level, 0.0) for h in hazards) / len(hazards)


def local_train_weights(
    global_weights: Dict[str, float],
    assessments: List[AssessmentResult],
    lr: float = 0.01
) -> Dict[str, float]:
    updated = global_weights.copy()

    for ar in assessments:
        features = extract_features(ar)
        hazard_signal = extract_hazard_signal(ar.hazards)

        prediction = (
            updated["w1"] * hazard_signal
            + updated["w2"] * features["compliance"]
            + updated["w3"] * features["structural"]
            + updated["w5"] * features["financial"]
        )

        error = features["safety"] - prediction

        updated["w1"] += lr * error * hazard_signal
        updated["w2"] += lr * error * features["compliance"]
        updated["w3"] += lr * error * features["structural"]
        updated["w5"] += lr * error * features["financial"]

    return updated


async def train_locally_and_upload(
    session: AsyncSession,
    experiment_id: int,
    project_id: int,
    user_id: int
) -> Dict[str, float]:
    # 1. Pull global model
    global_model = await get_global_model(session, experiment_id)
    if not global_model:
        raise ValueError("Global model not found")

    # 2. Pull assessments for project
    stmt = (
        select(AssessmentResult)
        .where(AssessmentResult.project_id == project_id)
    )
    results = (await session.execute(stmt)).scalars().all()

    if not results:
        raise ValueError("No assessments for project")

    # 3. Load hazards
    for ar in results:
        await session.refresh(ar, attribute_names=["hazards"])

    # 4. Local training
    updated_weights = local_train_weights(
        global_model.weights,
        results
    )

    # 5. Upload weights (Envoy action)
    await upload_weights(
        session=session,
        experiment_id=experiment_id,
        uploader_id=user_id,
        weights=updated_weights
    )

    return updated_weights
