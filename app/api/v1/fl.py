from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.schemas.fl import (
    EnvoyTrainRequest,
    FLExperimentCreate,
    FLExperimentRead,
    FLInferenceRequest,
    FLInferenceResponse,
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
    get_global_model,
    
)
from app.models.fl_participant import FLParticipant
from app.models.fl_weights_upload import FLWeightsUpload

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
        participant = await join_experiment(session, experiment_id, user.id)
        return JoinExperimentResponse(
            participant_id=participant.id,
            experiment_id=participant.experiment_id,
            user_id=participant.user_id
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Experiment not found")


# -----------------------------
# Participant Helper Endpoint
# -----------------------------

@router.get("/experiments/{experiment_id}/my-participant-id")
async def api_get_participant_id(
    experiment_id: int,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(FLParticipant).where(
        FLParticipant.experiment_id == experiment_id,
        FLParticipant.user_id == user.id
    )
    participant = (await session.execute(stmt)).scalars().first()
    if not participant:
        raise HTTPException(status_code=404, detail="User not a participant")
    return {"participant_id": participant.id}


# -----------------------------
# Start Experiment
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
    payload: EnvoyTrainRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Trigger local training for a participant (envoy) on AssessmentResult dataset
    and immediately aggregate into global model.
    """
    try:
        result = await envoy_train(
            session=session,
            experiment_id=experiment_id,
            participant_id=payload.participant_id,
            project_id=payload.project_id,
            epochs=payload.epochs,
            lr=payload.lr,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

# -----------------------------
# Upload Weights (optional)
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
# Aggregation Endpoint
# -----------------------------

@router.post("/experiments/{experiment_id}/aggregate")
async def api_aggregate_round(experiment_id: int, session: AsyncSession = Depends(get_session)):
    try:
        agg_weights = await aggregate_round(session, experiment_id)
        if not agg_weights:
            raise HTTPException(status_code=400, detail="Not enough envoy updates to aggregate")
        # Update global model after aggregation
        await update_global_model(session, experiment_id, agg_weights)
        # Return contributors for transparency
        stmt = select(FLWeightsUpload.uploader_id).where(
            and_(
                FLWeightsUpload.experiment_id == experiment_id,
                FLWeightsUpload.round == (await get_experiment(session, experiment_id)).current_round
            )
        )
        res = await session.execute(stmt)
        contributor_ids = [uid for (uid,) in res.fetchall()]
        return {"aggregated_weights": agg_weights, "contributors": contributor_ids}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -----------------------------
# Global Model Inference (FIXED)
# -----------------------------

@router.post(
    "/experiments/{experiment_id}/infer",
    response_model=FLInferenceResponse
)
async def api_infer(
    experiment_id: int,
    payload: FLInferenceRequest,
    session: AsyncSession = Depends(get_session),
):
    import torch
    import torch.nn as nn

    # Fetch global model
    global_model = await get_global_model(session, experiment_id)
    if not global_model:
        raise HTTPException(
            status_code=404,
            detail="Global model not available yet"
        )

    if not payload.inputs:
        raise HTTPException(
            status_code=400,
            detail="Input batch cannot be empty"
        )

    input_dim = len(payload.inputs[0])

    # --- Model architecture MUST match training ---
    class InferenceModel(nn.Module):
        def __init__(self, input_dim: int):
            super().__init__()
            self.linear = nn.Linear(input_dim, 1)

        def forward(self, x):
            return self.linear(x)

    model = InferenceModel(input_dim=input_dim)

    # --- FIX: Convert persisted lists → tensors ---
    try:
        state_dict = {
            k: torch.tensor(v, dtype=torch.float32)
            for k, v in global_model.weights.items()
        }
        model.load_state_dict(state_dict)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load global model weights: {str(e)}"
        )

    model.eval()

    # --- Run inference ---
    with torch.no_grad():
        x = torch.tensor(payload.inputs, dtype=torch.float32)
        outputs = model(x).squeeze(dim=-1)

    return FLInferenceResponse(
        predictions=outputs.tolist(),
        model_round=global_model.round,
        experiment_id=experiment_id
    )


# -----------------------------
# End of File
# -----------------------------
