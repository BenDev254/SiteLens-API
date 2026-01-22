import asyncio
import logging
import random
from sqlalchemy import select
from app.core.database import AsyncSessionLocal

# -----------------------------
# Import FL services & models
# -----------------------------
from app.models.fl_experiment import FLExperiment
from app.models.fl_participant import FLParticipant
from app.models.fl_weights_upload import FLWeightsUpload
from app.services.fl_service import (
    create_experiment,
    join_experiment,
    start_experiment,
    envoy_train,
    aggregate_round,
    get_global_model
)

# -----------------------------
# Synthetic dataset generator
# -----------------------------
def generate_synthetic_dataset(num_samples=50, noise=0.05):
    """Generates a small synthetic dataset for training"""
    weights = [0.1, 0.2, 0.15, 0.25, 0.2, 0.1]
    dataset = []
    for _ in range(num_samples):
        features = [random.random() for _ in range(6)]
        label = sum(f * w for f, w in zip(features, weights)) + random.uniform(-noise, noise)
        dataset.append({"features": features, "label": label})
    return dataset

# -----------------------------
# Logging Setup
# -----------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("fl_test_pipeline")

# -----------------------------
# FL Pipeline: Create fresh experiment
# -----------------------------
async def run_fl_pipeline():
    async with AsyncSessionLocal() as session:
        # -----------------------------
        # 1. Create new experiment
        # -----------------------------
        exp = await create_experiment(session, "Kenya Construction FL Test", participant_threshold=2)
        logger.info(f"Created experiment: ID={exp.id}, Name={exp.name}, Status={exp.status}")

        # -----------------------------
        # 2. Register participants
        # -----------------------------
        user_ids = [4, 8]  # ensure these exist in your DB
        participants = []

        for uid in user_ids:
            participant = await join_experiment(session, exp.id, uid)
            participants.append(participant)
            logger.info(f"Participant user_id={uid} joined (FLParticipant id={participant.id})")

        # -----------------------------
        # 3. Start experiment
        # -----------------------------
        start_info = await start_experiment(session, exp.id)
        logger.info(f"Experiment started: Status={start_info['status']}")

        # -----------------------------
        # 4. Federated Learning Rounds
        # -----------------------------
        NUM_ROUNDS = 3
        for rnd in range(NUM_ROUNDS):
            logger.info(f"\n=== FL Round {rnd + 1} ===")
            for participant in participants:
                dataset = generate_synthetic_dataset(num_samples=50, noise=0.05)
                try:
                    train_info = await envoy_train(
                        session,
                        experiment_id=exp.id,
                        participant_id=participant.id,  # DB participant ID
                        local_dataset=dataset,          # Now matches updated signature
                        epochs=5,
                        lr=0.01,
                    )
                    logger.info(
                        f"Participant user_id={participant.user_id} (FLParticipant id={participant.id}) "
                        f"trained on {train_info.get('samples_trained', 0)} samples"
                    )
                except Exception as e:
                    logger.error(f"Envoy training failed for participant_id={participant.id}: {e}")

            # -----------------------------
            # 5. Aggregate global model
            # -----------------------------
            current_round = exp.current_round
            agg_weights = await aggregate_round(session, exp.id)
            if agg_weights:
                logger.info(f"Aggregated global model weights updated for round {current_round}")
                # Fetch contributors for this round
                stmt = select(FLWeightsUpload.uploader_id).where(
                    FLWeightsUpload.experiment_id == exp.id,
                    FLWeightsUpload.round == current_round
                )
                res = await session.execute(stmt)
                contributor_ids = [uid for (uid,) in res.fetchall()]
                logger.info(f"Participants contributing this round: {contributor_ids}")
            else:
                logger.warning(f"Not enough participant uploads to aggregate round {current_round}")

            # -----------------------------
            # 6. Fetch latest global model
            # -----------------------------
            global_model = await get_global_model(session, exp.id)
            if global_model:
                logger.info(f"Global model round {global_model.round} updated")

        logger.info("\n=== FL Pipeline Complete ===")

# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":
    asyncio.run(run_fl_pipeline())
