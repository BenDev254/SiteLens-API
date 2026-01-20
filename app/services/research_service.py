from typing import List, Optional, Dict, Any
from datetime import datetime, date
import io
import csv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research_log import ResearchLog


async def log_interaction(session: AsyncSession, project_id: int, user_id: Optional[int], action: str, details: Optional[Dict[str, Any]] = None) -> ResearchLog:
    rec = ResearchLog(project_id=project_id, user_id=user_id, action=action, details=details)
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec


async def list_history(session: AsyncSession, project_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None, limit: int = 100, offset: int = 0) -> List[ResearchLog]:
    stmt = select(ResearchLog)
    if project_id:
        stmt = stmt.where(ResearchLog.project_id == project_id)
    if start:
        stmt = stmt.where(ResearchLog.created_at >= datetime.combine(start, datetime.min.time()))
    if end:
        stmt = stmt.where(ResearchLog.created_at <= datetime.combine(end, datetime.max.time()))
    stmt = stmt.offset(offset).limit(limit)
    res = await session.execute(stmt)
    return res.scalars().all()


async def export_history(session: AsyncSession, project_id: Optional[int] = None, start: Optional[date] = None, end: Optional[date] = None, fmt: str = "csv") -> bytes:
    items = await list_history(session, project_id=project_id, start=start, end=end, limit=10000, offset=0)
    if fmt == "json":
        import json

        payload = [r.model_dump() for r in items]
        return json.dumps(payload, default=str).encode("utf-8")

    # default CSV
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "project_id", "user_id", "action", "details", "created_at"])
    for r in items:
        writer.writerow([r.id, r.project_id, r.user_id, r.action, (r.details or {}).__repr__(), r.created_at.isoformat()])
    return buf.getvalue().encode("utf-8")
