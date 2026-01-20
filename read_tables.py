import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

from app.models.fl_experiment import FLExperiment
from app.models.fl_participant import FLParticipant
from app.models.envoy_local_model import EnvoyLocalModel

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def inspect_tables():
    async with async_session() as session:
        # List all experiments
        experiments = (await session.execute(select(FLExperiment))).scalars().all()
        print("\n--- FL Experiments ---")
        for e in experiments:
            print(f"id={e.id}, name={e.name}, status={e.status}, current_round={e.current_round}")

        # List all participants
        participants = (await session.execute(select(FLParticipant))).scalars().all()
        print("\n--- FL Participants ---")
        for p in participants:
            print(f"id={p.id}, user_id={p.user_id}, experiment_id={p.experiment_id}, joined_at={p.joined_at}")

        # List all local models
        local_models = (await session.execute(select(EnvoyLocalModel))).scalars().all()
        print("\n--- Envoy Local Models ---")
        for lm in local_models:
            print(f"id={lm.id}, participant_id={lm.participant_id}, experiment_id={lm.experiment_id}, round={lm.round}")

asyncio.run(inspect_tables())
