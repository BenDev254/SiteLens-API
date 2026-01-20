from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.live_telemetry import LiveTelemetry
from app.models.live_alert import LiveAlert
from app.models.live_config import LiveConfig


async def persist_telemetry(session: AsyncSession, project_id: int, metric: str, value: float, tags: Optional[Dict[str, Any]] = None) -> LiveTelemetry:
    rec = LiveTelemetry(project_id=project_id, metric=metric, value=value, tags=tags)
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec


async def list_telemetry(session: AsyncSession, project_id: int, limit: int = 100, offset: int = 0) -> List[LiveTelemetry]:
    stmt = select(LiveTelemetry).where(LiveTelemetry.project_id == project_id).order_by(LiveTelemetry.recorded_at.desc()).offset(offset).limit(limit)
    res = await session.execute(stmt)
    return res.scalars().all()


async def create_alert(session: AsyncSession, project_id: int, alert_type: str, severity: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> LiveAlert:
    a = LiveAlert(project_id=project_id, alert_type=alert_type, severity=severity, message=message, metadata=metadata)
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return a


async def acknowledge_alert(session: AsyncSession, alert_id: int, ack_by: int) -> LiveAlert:
    alert = await session.get(LiveAlert, alert_id)
    if not alert:
        raise ValueError("alert not found")
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_by = ack_by
    alert.acknowledged_at = datetime.utcnow()
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


async def get_alerts(session: AsyncSession, project_id: int, status: Optional[str] = None) -> List[LiveAlert]:
    stmt = select(LiveAlert).where(LiveAlert.project_id == project_id)
    if status:
        stmt = stmt.where(LiveAlert.status == status)
    stmt = stmt.order_by(LiveAlert.created_at.desc())
    res = await session.execute(stmt)
    return res.scalars().all()


async def get_or_create_config(session: AsyncSession, project_id: int) -> LiveConfig:
    stmt = select(LiveConfig).where(LiveConfig.project_id == project_id).order_by(LiveConfig.updated_at.desc()).limit(1)
    res = await session.execute(stmt)
    cfg = res.scalars().first()
    if cfg:
        return cfg
    cfg = LiveConfig(project_id=project_id, config={})
    session.add(cfg)
    await session.commit()
    await session.refresh(cfg)
    return cfg


async def update_config(session: AsyncSession, project_id: int, config: Dict[str, Any]) -> LiveConfig:
    cfg = await get_or_create_config(session, project_id)
    cfg.config = config
    cfg.updated_at = datetime.utcnow()
    session.add(cfg)
    await session.commit()
    await session.refresh(cfg)
    return cfg


async def get_status_summary(session: AsyncSession, project_id: int) -> Dict[str, Any]:
    # Very simple summary: latest telemetry values and count of open alerts
    latest = await session.execute(select(LiveTelemetry).where(LiveTelemetry.project_id == project_id).order_by(LiveTelemetry.recorded_at.desc()).limit(20))
    latest_items = latest.scalars().all()
    alerts = await session.execute(select(LiveAlert).where(LiveAlert.project_id == project_id, LiveAlert.status != 'RESOLVED').order_by(LiveAlert.created_at.desc()).limit(50))
    alert_items = alerts.scalars().all()
    # return simple summary
    return {
        "project_id": project_id,
        "latest_telemetry": [t.model_dump() for t in latest_items],
        "open_alerts": [a.model_dump() for a in alert_items],
    }
