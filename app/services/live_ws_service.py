from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript import Transcript


async def persist_transcript(session: AsyncSession, project_id: int, user_id: Optional[int], text: str, source: str = "live_ws") -> Transcript:
    t = Transcript(project_id=project_id, user_id=user_id, text=text, source=source)
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t
