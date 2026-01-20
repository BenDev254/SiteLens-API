import random
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import torch
import torch.nn as nn
import torch.optim as optim

from app.models.envoy_local_model import EnvoyLocalModel
from app.models.fl_experiment import FLExperiment
from app.models.fl_participant import FLParticipant
from app.models.fl_weights_upload import FLWeightsUpload
from app.models.fl_global_model import FLGlobalModel

# -----------------------------
# PyTorch Linear Model Definition
# -----------------------------
class ConstructionLinearModel(nn.Module):
    """
    Simple linear regression model with 6 input features corresponding
    to construction KPIs: safety, compliance, materials, inspections, budget, overruns
    """
    def __init__(self, input_dim=6, output_dim=1):
        super().__init__()
        self.linear = nn.Linear(input_dim, output_dim)
    
    def forward(self, x):
        return self.linear(x)

# -----------------------------
# Default Model (used to initialize first global model)
# -----------------------------
def default_model_state_dict():
    """
    Returns a PyTorch model's state_dict initialized randomly
    """
    model = ConstructionLinearModel()
    return model.state_dict()

# -----------------------------
# Experiments
# -----------------------------
async def list_experiments(session: AsyncSession) -> List[FLExperiment]:
    stmt = select(FLExperiment)
    res = await session.execute(stmt)
    return res.scalars().all()


async def create_experiment(
    session: AsyncSession,
    name: str,
    params: Optional[Dict[str, Any]] = None,
    participant_threshold: int = 3
) -> FLExperiment:
    """
    Creates a new FL experiment with initial global model
    """
    exp = FLExperiment(
        name=name,
        params=params or {"model": "kenya-construction-linear", "aggregation": "fedavg"},
        participant_threshold=participant_threshold,
        current_round=0,
        status="CREATED"
    )
    session.add(exp)
    await session.flush()

    # Initialize first global model with JSON-serializable weights
    global_model = FLGlobalModel(
        experiment_id=exp.id,
        round=0,
        weights={k: v.tolist() for k, v in default_model_state_dict().items()}
    )
    session.add(global_model)
    await session.commit()
    await session.refresh(exp)
    return exp


async def get_experiment(session: AsyncSession, experiment_id: int) -> Optional[FLExperiment]:
    return await session.get(FLExperiment, experiment_id)


# -----------------------------
# Participants
# -----------------------------
async def join_experiment(session: AsyncSession, experiment_id: int, user_id: int) -> FLParticipant:
    """
    Registers a participant in an experiment
    """
    exp = await session.get(FLExperiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")

    stmt = select(FLParticipant).where(
        FLParticipant.experiment_id == experiment_id,
        FLParticipant.user_id == user_id
    )
    res = await session.execute(stmt)
    p = res.scalars().first()
    if p:
        return p

    p = FLParticipant(
        experiment_id=experiment_id,
        user_id=user_id,
        joined_at=datetime.utcnow()
    )
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return p


# -----------------------------
# Global Model
# -----------------------------
async def get_global_model(session: AsyncSession, experiment_id: int) -> Optional[FLGlobalModel]:
    stmt = (
        select(FLGlobalModel)
        .where(FLGlobalModel.experiment_id == experiment_id)
        .order_by(FLGlobalModel.round.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalars().first()


# -----------------------------
# Weight Uploads (Participants)
# -----------------------------
async def upload_weights(
    session: AsyncSession,
    experiment_id: int,
    uploader_id: int,
    weights: Any,
    dataset_size: int
) -> FLWeightsUpload:
    """
    Participant uploads locally trained model weights along with dataset size
    Ensures weights are JSON-serializable
    """
    exp = await session.get(FLExperiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")

    participant = await session.get(FLParticipant, uploader_id)
    if not participant or participant.experiment_id != experiment_id:
        raise PermissionError("not a participant")


    # Convert tensors/lists to ensure JSON-serializable
    weights_json = {k: (v if isinstance(v, list) else v.tolist()) for k, v in weights.items()}

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


async def get_uploads(session: AsyncSession, experiment_id: int) -> List[FLWeightsUpload]:
    stmt = select(FLWeightsUpload).where(FLWeightsUpload.experiment_id == experiment_id)
    res = await session.execute(stmt)
    return res.scalars().all()


# -----------------------------
# Aggregation (FedAvg)
# -----------------------------
async def aggregate_round(session: AsyncSession, experiment_id: int) -> Optional[Dict[str, Any]]:
    """
    Aggregates weights from all participant uploads using FedAvg (weighted by dataset size)
    Converts tensors to lists for JSON storage
    """
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

    # Initialize aggregation dictionary
    agg_state = {k: torch.zeros_like(torch.tensor(v)) for k, v in uploads[0].weights.items()}
    total_samples = sum(u.dataset_size for u in uploads)

    # Weighted FedAvg
    for k in agg_state.keys():
        agg_val = sum(
            torch.tensor(u.weights[k]) * (u.dataset_size / total_samples)
            for u in uploads
        )
        agg_state[k] = agg_val.tolist()  # convert tensor -> list for JSON storage

    # Save new global model
    global_model = FLGlobalModel(
        experiment_id=experiment_id,
        round=exp.current_round + 1,
        weights=agg_state
    )
    exp.current_round += 1
    exp.status = "TRAINING"

    session.add_all([global_model, exp])
    await session.commit()
    return agg_state


# -----------------------------
# Start Experiment
# -----------------------------
async def start_experiment(session: AsyncSession, experiment_id: int) -> Dict[str, Any]:
    exp = await session.get(FLExperiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")

    if exp.status != "CREATED":
        raise ValueError(f"experiment already {exp.status}")

    # Fetch all participants for this experiment
    stmt = select(FLParticipant).where(FLParticipant.experiment_id == experiment_id)
    participants = (await session.execute(stmt)).scalars().all()
    if not participants:
        raise ValueError("No participants registered for this experiment")

    # Fetch or initialize global model
    global_model = await get_global_model(session, experiment_id)
    if not global_model:
        global_model = FLGlobalModel(
            experiment_id=experiment_id,
            round=0,
            weights={k: v.tolist() for k, v in default_model_state_dict().items()}
        )
        session.add(global_model)
        await session.commit()
        await session.refresh(global_model)

    # Create local models for participants
    for p in participants:
        local_model_exists = await session.execute(
            select(EnvoyLocalModel).where(
                EnvoyLocalModel.experiment_id == experiment_id,
                EnvoyLocalModel.participant_id == p.id,
                EnvoyLocalModel.round == 0
            )
        )
        if not local_model_exists.scalars().first():
            local_model_entry = EnvoyLocalModel(
                experiment_id=experiment_id,
                participant_id=p.id,
                round=0,
                weights={k: (v if isinstance(v, list) else v.tolist()) for k, v in global_model.weights.items()}
            )
            session.add(local_model_entry)
            await session.commit()
            await session.refresh(local_model_entry)

    exp.status = "STARTED"
    session.add(exp)
    await session.commit()
    await session.refresh(exp)

    return {
        "experiment_id": exp.id,
        "status": exp.status,
        "envoys": [{"participant_id": p.id, "round": 0} for p in participants]
    }


# -----------------------------
# Envoy Local Training
# -----------------------------
async def envoy_train(
    session: AsyncSession,
    experiment_id: int,
    participant_id: int,  # this is now always DB participant.id
    local_dataset: list,
    epochs: int = 5,
    lr: float = 0.01
) -> dict:
    """Performs local training on participant's dataset using DB participant ID"""

    # Fetch experiment
    exp = await session.get(FLExperiment, experiment_id)
    if not exp:
        raise ValueError("experiment not found")

    # Fetch participant by DB ID
    participant = await session.get(FLParticipant, participant_id)
    if not participant or participant.experiment_id != experiment_id:
        raise ValueError("not a participant")

    # Fetch current local model
    stmt = select(EnvoyLocalModel).where(
        EnvoyLocalModel.experiment_id == experiment_id,
        EnvoyLocalModel.participant_id == participant_id,
        EnvoyLocalModel.round == exp.current_round
    )
    local_model_entry = (await session.execute(stmt)).scalars().first()
    if not local_model_entry:
        local_model_entry = EnvoyLocalModel(
            experiment_id=experiment_id,
            participant_id=participant_id,
            round=exp.current_round,
            weights={k: v.tolist() for k, v in default_model_state_dict().items()}
        )
        session.add(local_model_entry)
        await session.commit()
        await session.refresh(local_model_entry)

    # Initialize PyTorch model from stored weights
    model = ConstructionLinearModel()
    state_dict = {k: torch.tensor(v) for k, v in local_model_entry.weights.items()}
    model.load_state_dict(state_dict)
    model.train()

    optimizer = optim.SGD(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    # Prepare data
    X = torch.tensor([d["features"] for d in local_dataset], dtype=torch.float32)
    y = torch.tensor([[d["label"]] for d in local_dataset], dtype=torch.float32)

    for _ in range(epochs):
        optimizer.zero_grad()
        predictions = model(X)
        loss = loss_fn(predictions, y)
        loss.backward()
        optimizer.step()

    # Update local model entry with JSON-serializable weights
    local_model_entry.weights = {k: v.tolist() for k, v in model.state_dict().items()}
    await session.commit()
    await session.refresh(local_model_entry)

    # Upload trained weights
    await upload_weights(
        session, experiment_id, participant_id,
        local_model_entry.weights, len(local_dataset)
    )

    return {
        "participant_id": participant_id,
        "experiment_id": experiment_id,
        "round": exp.current_round,
        "trained_weights": local_model_entry.weights,
        "samples_trained": len(local_dataset)
    }

# -----------------------------
# Synthetic Dataset Helper
# -----------------------------
def generate_synthetic_dataset(num_samples: int = 50, noise: float = 0.05) -> List[Dict[str, Any]]:
    """
    Generates a small synthetic dataset for a participant.

    Features:
        - 6 features representing construction KPIs
        - Values are floats between 0 and 1
    Label:
        - Weighted sum of features + small noise
    """
    weights = [0.1, 0.2, 0.15, 0.25, 0.2, 0.1]
    dataset = []
    for _ in range(num_samples):
        features = [random.uniform(0, 1) for _ in range(6)]
        label = sum(f * w for f, w in zip(features, weights)) + random.uniform(-noise, noise)
        dataset.append({"features": features, "label": label})
    return dataset
