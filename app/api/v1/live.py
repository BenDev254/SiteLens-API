from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.live_alert import AlertStatus, LiveAlert


from app.core.database import get_session
from app.core.security import get_current_user
from app.services.live_service import (
    persist_telemetry,
    list_telemetry,
    create_alert,
    acknowledge_alert,
    get_alerts,
    get_or_create_config,
    update_config,
    get_status_summary,
)
from app.schemas.live import (
    TelemetryCreate,
    TelemetryRead,
    AlertCreate,
    AlertRead,
    AlertAckRequest,
    LiveConfigRead,
    LiveConfigUpdate,
)
from app.services.project_service import get_project, check_ownership

router = APIRouter(prefix="/live", tags=["live"])


@router.get("/status/{project_id}")
async def status(project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # anyone with access (owner or government) can view status
    if not await check_ownership(session, project, user) and user.role != 'GOVERNMENT':
        raise HTTPException(status_code=403, detail="Not owner")
    return await get_status_summary(session, project_id)


@router.post("/{project_id}/telemetry", response_model=TelemetryRead)
async def post_telemetry(project_id: int, payload: TelemetryCreate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user) and user.role != 'GOVERNMENT':
        raise HTTPException(status_code=403, detail="Not owner")
    rec = await persist_telemetry(session, project_id, payload.metric, payload.value, payload.tags)
    return TelemetryRead(**rec.model_dump())


@router.get("/{project_id}/telemetry/history", response_model=list)
async def telemetry_history(project_id: int, limit: int = 100, offset: int = 0, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user) and user.role != 'GOVERNMENT':
        raise HTTPException(status_code=403, detail="Not owner")
    items = await list_telemetry(session, project_id, limit=limit, offset=offset)
    return [TelemetryRead(**i.model_dump()) for i in items]


@router.post("/{project_id}/alerts", response_model=AlertRead)
async def post_alert(project_id: int, payload: AlertCreate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # either system or owner can post alerts; simple check requires owner or government
    if not await check_ownership(session, project, user) and user.role != 'GOVERNMENT':
        raise HTTPException(status_code=403, detail="Not owner")
    a = await create_alert(session, project_id, payload.alert_type, payload.severity, payload.message, payload.metadata)
    return AlertRead(**a.model_dump())




@router.post(
    "/{project_id}/alerts/{alert_id}/acknowledge",
    response_model=AlertRead,
)
async def acknowledge(
    project_id: int,
    alert_id: int,
    _: AlertAckRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not await check_ownership(session, project, user) and user.role != "GOVERNMENT":
        raise HTTPException(status_code=403, detail="Not owner")

    stmt = select(LiveAlert).where(
        LiveAlert.id == alert_id,
        LiveAlert.project_id == project_id,
    )
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found for project")

    if alert.status != AlertStatus.OPEN:
        raise HTTPException(
            status_code=409,
            detail=f"Alert already {alert.status.lower()}",
        )

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by = user.id
    alert.acknowledged_at = datetime.utcnow()

    session.add(alert)
    await session.commit()
    await session.refresh(alert)

    return AlertRead.model_validate(alert, from_attributes=True)







@router.get("/{project_id}/alerts", response_model=list)
async def get_project_alerts(project_id: int, status: Optional[str] = None, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user) and user.role != 'GOVERNMENT':
        raise HTTPException(status_code=403, detail="Not owner")
    items = await get_alerts(session, project_id, status=status)
    return [AlertRead(**i.model_dump()) for i in items]


@router.get("/config/{project_id}", response_model=LiveConfigRead)
async def get_config(project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user) and user.role != 'GOVERNMENT':
        raise HTTPException(status_code=403, detail="Not owner")
    cfg = await get_or_create_config(session, project_id)
    return LiveConfigRead(**cfg.model_dump())


@router.put("/config/{project_id}", response_model=LiveConfigRead)
async def put_config(project_id: int, payload: LiveConfigUpdate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # only owner or government can update
    if not await check_ownership(session, project, user) and user.role != 'GOVERNMENT':
        raise HTTPException(status_code=403, detail="Not owner")
    cfg = await update_config(session, project_id, payload.config)
    return LiveConfigRead(**cfg.model_dump())
