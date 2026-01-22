import random
import math
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import torch
import torch.nn as nn
import torch.optim as optim

from app.models.assessment_result import AssessmentResult
from app.models.envoy_local_model import EnvoyLocalModel
from app.models.fl_experiment import FLExperiment
from app.models.fl_participant import FLParticipant
from app.models.fl_weights_upload import FLWeightsUpload
from app.models.fl_global_model import FLGlobalModel

# ============================================================
# Utils
# ============================================================

def safe_float(x: float, default: float = 0.0) -> float:
    if x is None:
        return default
    if not isinstance(x, (int, float)):
        return default
    if math.isnan(x) or math.isinf(x):
        return default
    return float(x)


def sanitize_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_json(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
        return obj
    return obj

# ============================================================
# PyTorch Model
# ============================================================

class ConstructionLinearModel(nn.Module):
    def __init__(self, input_dim: int = 6, output_dim: int = 1):
        super().__init__()
        self.linear = nn.Linear(input_dim, output_dim)

    def forward(self, x):
        return self.linear(x)


def default_model_state_dict() -> Dict[str, torch.Tensor]:
    return ConstructionLinearModel().state_dict()

# ============================================================
# Experiments
# ============================================================

async def list_experiments(session: AsyncSession) -> List[FLExperiment]:
    res = await session.execute(select(FLExperiment))
    return res.scalars().all()


async def get_experiment(
    session: AsyncSession,
    experiment_id: int
) -> Optional[FLExperiment]:
    return await session.get(FLExperiment, experiment_id)


async def create_experiment(
    session: AsyncSession,
    name: str,
    params: Optional[Dict[str, Any]] = None,
    participant_threshold: int = 3
) -> FLExperiment:

    exp = FLExperiment(
        name=name,
        params=params or {
            "model": "construction-linear",
            "aggregation": "fedavg"
        },
        participant_threshold=participant_threshold,
        current_round=0,
        status="CREATED"
    )
    session.add(exp)
    await session.flush()

    global_model = FLGlobalModel(
        experiment_id=exp.id,
        round=0,
        weights=sanitize_json({
            k: v.tolist() for k, v in default_model_state_dict().items()
        })
    )
    session.add(global_model)

    await session.commit()
    await session.refresh(exp)
    return exp

# ============================================================
# Participants
# ============================================================

async def join_experiment(
    session: AsyncSession,
    experiment_id: int,
    user_id: int
) -> FLParticipant:

    exp = await session.get(FLExperiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")

    stmt = select(FLParticipant).where(
        FLParticipant.experiment_id == experiment_id,
        FLParticipant.user_id == user_id
    )
    existing = (await session.execute(stmt)).scalars().first()
    if existing:
        return existing

    participant = FLParticipant(
        experiment_id=experiment_id,
        user_id=user_id,
        joined_at=datetime.utcnow()
    )
    session.add(participant)
    await session.commit()
    await session.refresh(participant)
    return participant

# ============================================================
# Global Model
# ============================================================

async def get_global_model(
    session: AsyncSession,
    experiment_id: int
) -> Optional[FLGlobalModel]:

    stmt = (
        select(FLGlobalModel)
        .where(FLGlobalModel.experiment_id == experiment_id)
        .order_by(FLGlobalModel.round.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalars().first()

# ============================================================
# Weight Uploads
# ============================================================

async def upload_weights(
    session: AsyncSession,
    experiment_id: int,
    uploader_id: int,
    weights: Dict[str, Any],
    dataset_size: int
) -> FLWeightsUpload:

    exp = await session.get(FLExperiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")

    participant = await session.get(FLParticipant, uploader_id)
    if not participant or participant.experiment_id != experiment_id:
        raise PermissionError("not a participant")

    weights_json = sanitize_json({
        k: v if isinstance(v, list) else v.tolist()
        for k, v in weights.items()
    })

    upload = FLWeightsUpload(
        experiment_id=experiment_id,
        uploader_id=participant.user_id,
        round=exp.current_round,
        weights=weights_json,
        dataset_size=dataset_size
    )
    session.add(upload)
    await session.commit()
    await session.refresh(upload)
    return upload


async def get_uploads(
    session: AsyncSession,
    experiment_id: int
) -> List[FLWeightsUpload]:
    res = await session.execute(
        select(FLWeightsUpload).where(
            FLWeightsUpload.experiment_id == experiment_id
        )
    )
    return res.scalars().all()

# ============================================================
# Aggregation (FedAvg)
# ============================================================

async def aggregate_round(
    session: AsyncSession,
    experiment_id: int
) -> Optional[Dict[str, Any]]:

    exp = await session.get(FLExperiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")

    stmt = select(FLWeightsUpload).where(
        FLWeightsUpload.experiment_id == experiment_id,
        FLWeightsUpload.round == exp.current_round
    )
    uploads = (await session.execute(stmt)).scalars().all()

    if len(uploads) < exp.participant_threshold:
        return None

    total_samples = sum(u.dataset_size for u in uploads)

    agg_state = {
        k: torch.zeros_like(torch.tensor(v))
        for k, v in uploads[0].weights.items()
    }

    for k in agg_state.keys():
        agg_state[k] = sum(
            torch.tensor(u.weights[k]) * (u.dataset_size / total_samples)
            for u in uploads
        )

    agg_state_json = sanitize_json({
        k: v.tolist() for k, v in agg_state.items()
    })

    global_model = FLGlobalModel(
        experiment_id=experiment_id,
        round=exp.current_round + 1,
        weights=agg_state_json
    )

    exp.current_round += 1
    exp.status = "TRAINING"

    session.add_all([global_model, exp])
    await session.commit()
    return agg_state_json

# ============================================================
# Start Experiment
# ============================================================

async def start_experiment(
    session: AsyncSession,
    experiment_id: int
) -> Dict[str, Any]:

    exp = await session.get(FLExperiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")

    if exp.status != "CREATED":
        raise ValueError("experiment already started")

    participants = (
        await session.execute(
            select(FLParticipant).where(
                FLParticipant.experiment_id == experiment_id
            )
        )
    ).scalars().all()

    if not participants:
        raise ValueError("no participants registered")

    exp.status = "STARTED"
    await session.commit()

    return {
        "experiment_id": exp.id,
        "status": exp.status,
        "participants": [p.id for p in participants],
        "round": exp.current_round
    }

# ============================================================
# Assessment Dataset Loader
# ============================================================

async def get_assessment_dataset(
    session: AsyncSession,
    project_id: int
) -> List[Dict[str, Any]]:

    stmt = (
        select(AssessmentResult)
        .where(AssessmentResult.project_id == project_id)
        .options(selectinload(AssessmentResult.hazards))
    )

    results = (await session.execute(stmt)).scalars().all()
    now = datetime.now(timezone.utc)

    dataset: List[Dict[str, Any]] = []

    for r in results:
        age_seconds = max(
            (now - r.created_at.replace(tzinfo=timezone.utc)).total_seconds(),
            0.0
        )

        f6 = 1.0 / (1.0 + age_seconds / 86400.0)

        features = [
            safe_float(r.score),
            safe_float(len(str(r.gemini_response)) if r.gemini_response else 0),
            safe_float(len(r.hazards)),
            safe_float(1.0 if r.image_path else 0.0),
            safe_float(r.project_id / 1000.0),
            safe_float(f6),
        ]

        dataset.append({
            "features": features,
            "label": safe_float(r.score),
        })

    return dataset

# ============================================================
# Envoy Training
# ============================================================

async def envoy_train(
    session: AsyncSession,
    experiment_id: int,
    participant_id: int,
    project_id: int,
    epochs: int = 5,
    lr: float = 0.01
) -> Dict[str, Any]:

    exp = await session.get(FLExperiment, experiment_id)
    if not exp or exp.status not in {"STARTED", "TRAINING"}:
        raise ValueError("experiment not active")

    participant = await session.get(FLParticipant, participant_id)
    if not participant or participant.experiment_id != experiment_id:
        raise ValueError("not a participant")

    local_dataset = await get_assessment_dataset(session, project_id)
    if not local_dataset:
        raise ValueError("no dataset found")

    global_model = await get_global_model(session, experiment_id)
    if not global_model:
        global_model = FLGlobalModel(
            experiment_id=experiment_id,
            round=0,
            weights=sanitize_json({
                k: v.tolist() for k, v in default_model_state_dict().items()
            })
        )
        session.add(global_model)
        await session.commit()
        await session.refresh(global_model)

    model = ConstructionLinearModel()
    model.load_state_dict({
        k: torch.tensor(v, dtype=torch.float32)
        for k, v in global_model.weights.items()
    })
    model.train()

    optimizer = optim.SGD(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    X = torch.tensor(
        [d["features"] for d in local_dataset],
        dtype=torch.float32
    )
    y = torch.tensor(
        [[d["label"]] for d in local_dataset],
        dtype=torch.float32
    )

    for _ in range(epochs):
        optimizer.zero_grad()
        preds = model(X)
        loss = loss_fn(preds, y)
        loss.backward()
        optimizer.step()

    trained_weights = sanitize_json({
        k: v.tolist() for k, v in model.state_dict().items()
    })

    await upload_weights(
        session=session,
        experiment_id=experiment_id,
        uploader_id=participant_id,
        weights=trained_weights,
        dataset_size=len(local_dataset)
    )

    await aggregate_round(session, experiment_id)

    return {
        "experiment_id": experiment_id,
        "participant_id": participant_id,
        "round": exp.current_round,
        "samples_trained": len(local_dataset),
        "loss": safe_float(loss.item())
    }
