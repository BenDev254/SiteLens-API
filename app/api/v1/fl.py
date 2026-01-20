from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.fl import (
    FLExperimentCreate,
    FLExperimentRead,
    JoinExperimentRequest,
    JoinExperimentResponse,
    WeightsUploadRequest,
    WeightsUploadResponse,
)
from app.core.database import get_session
from app.core.security import get_current_user
from app.services.fl_service import (
    list_experiments,
    create_experiment,
    join_experiment,
    upload_weights,
    get_experiment,
    get_uploads,
    start_experiment,
    envoy_train,
    aggregate_round,
    get_global_model
)

router = APIRouter(prefix="/api/v1/fl", tags=["federated-learning"])

# -----------------------------
# Experiment Endpoints
# -----------------------------

@router.get("/experiments", response_model=List[FLExperimentRead])
async def api_list_experiments(session: AsyncSession = Depends(get_session)):
    return await list_experiments(session)


@router.post("/experiments", response_model=FLExperimentRead)
async def api_create_experiment(
    payload: FLExperimentCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user)
):
    exp = await create_experiment(
        session,
        name=payload.name,
        params=payload.params or {},
        participant_threshold=payload.participant_threshold
    )
    return exp


@router.get("/experiments/{experiment_id}", response_model=FLExperimentRead)
async def api_get_experiment(experiment_id: int, session: AsyncSession = Depends(get_session)):
    exp = await get_experiment(session, experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


# -----------------------------
# Experiment Join
# -----------------------------

@router.post("/experiments/{experiment_id}/join", response_model=JoinExperimentResponse)
async def api_join_experiment(
    experiment_id: int,
    payload: JoinExperimentRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user)
):
    try:
        p = await join_experiment(session, experiment_id, user.id)
        return JoinExperimentResponse(
            participant_id=p.id,
            experiment_id=p.experiment_id,
            user_id=p.user_id
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Experiment not found")


# -----------------------------
# Start Experiment (Send Training Artifacts to Envoys)
# -----------------------------

@router.post("/experiments/{experiment_id}/start")
async def api_start_experiment(experiment_id: int, session: AsyncSession = Depends(get_session)):
    try:
        data = await start_experiment(session, experiment_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# Envoy Local Training
# -----------------------------

@router.post("/experiments/{experiment_id}/envoy/train")
async def api_envoy_train(
    experiment_id: int,
    participant_id: int,
    weights: Dict[str, Any],
    session: AsyncSession = Depends(get_session)
):
    try:
        result = await envoy_train(session, experiment_id, participant_id, weights)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -----------------------------
# Upload Weights (optional, legacy)
# -----------------------------

@router.post("/weights/upload", response_model=WeightsUploadResponse)
async def api_upload_weights(
    payload: WeightsUploadRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user)
):
    try:
        upload = await upload_weights(
            session,
            payload.experiment_id,
            user.id,
            weights=payload.weights,
        )
        return WeightsUploadResponse(
            upload_id=upload.id,
            experiment_id=upload.experiment_id,
            uploader_id=upload.uploader_id
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Experiment not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not a participant")


@router.get("/experiments/{experiment_id}/uploads")
async def api_get_uploads(experiment_id: int, session: AsyncSession = Depends(get_session)):
    return await get_uploads(session, experiment_id)


# -----------------------------
# Aggregation Endpoint (Director)
# -----------------------------

@router.post("/experiments/{experiment_id}/aggregate")
async def api_aggregate_round(experiment_id: int, session: AsyncSession = Depends(get_session)):
    try:
        avg = await aggregate_round(session, experiment_id)
        if not avg:
            raise HTTPException(status_code=400, detail="Not enough envoy updates to aggregate")
        return {"aggregated_weights": avg}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -----------------------------
# Global Model Inference
# -----------------------------

@router.post("/experiments/{experiment_id}/infer")
async def api_infer(
    experiment_id: int,
    input_weights: Dict[str, Any],
    session: AsyncSession = Depends(get_session)
):
    global_model = await get_global_model(session, experiment_id)
    if not global_model:
        raise HTTPException(status_code=404, detail="Global model not found")

    # simple weighted sum PoC
    prediction = sum(
        input_weights.get(k, 0.0) * global_model.weights.get(k, 0.0)
        for k in global_model.weights
    )

    return {
        "prediction": prediction,
        "global_weights": global_model.weights
    }

    
# -----------------------------
# End of File
# -----------------------------