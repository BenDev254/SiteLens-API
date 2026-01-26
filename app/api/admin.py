from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import require_role
from app.models.user import Role
from app.models.admin_audit import AdminAudit
from app.core.database import get_session
from app.services import admin_service
from app.schemas.admin import (
    ContractorRead,
    ProfessionalRead,
    FineCreate,
    FineRead,
    RevenueStats,
    PolicyArchiveRequest,
    AdminAIConfigRead,
    AdminAIConfigUpdate,
    AuditRecord,
    ContractorCreate,
    ProfessionalCreate,
)

router = APIRouter()


@router.post("/contractors", response_model=ContractorRead)
async def create_contractor(
    payload: ContractorCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(Role.GOVERNMENT)),
):
    contractor = await admin_service.create_contractor(session, payload)

    await admin_service.record_admin_audit(
        session,
        user.id,
        "create_contractor",
        resource_type="contractor",
        resource_id=contractor.id,
        details={"name": contractor.name, "email": user.email},
    )

    return contractor


@router.delete("/contractors/{contractor_id}")
async def delete_contractor(
    contractor_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(Role.GOVERNMENT)),
):
    try:
        await admin_service.delete_contractor(session, contractor_id)

        await admin_service.record_admin_audit(
            session,
            user.id,
            "delete_contractor",
            resource_type="contractor",
            resource_id=contractor_id,
        )

        return {"ok": True, "contractor_id": contractor_id}
    except ValueError:
        raise HTTPException(status_code=404, detail="contractor not found")




@router.get("/contractors", response_model=List[ContractorRead])
async def get_contractors(session: AsyncSession = Depends(get_session), user=Depends(require_role(Role.GOVERNMENT))):
    items = await admin_service.list_contractors(session)
    await admin_service.record_admin_audit(session, user.id, "list_contractors", resource_type="contractor")
    return items



@router.post("/professionals", response_model=ProfessionalRead)
async def create_professional(
    payload: ProfessionalCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(Role.GOVERNMENT)),
):
    professional = await admin_service.create_professional(session, payload)

    await admin_service.record_admin_audit(
        session,
        user.id,
        "create_professional",
        resource_type="professional",
        resource_id=professional.id,
        details={"name": professional.name, "email": professional.email},
    )

    return professional


@router.delete("/professionals/{professional_id}")
async def delete_professional(
    professional_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(Role.GOVERNMENT)),
):
    try:
        await admin_service.delete_professional(session, professional_id)

        await admin_service.record_admin_audit(
            session,
            user.id,
            "delete_professional",
            resource_type="professional",
            resource_id=professional_id,
        )

        return {"ok": True, "professional_id": professional_id}
    except ValueError:
        raise HTTPException(status_code=404, detail="professional not found")



@router.get("/professionals", response_model=List[ProfessionalRead])
async def get_professionals(session: AsyncSession = Depends(get_session), user=Depends(require_role(Role.GOVERNMENT))):
    items = await admin_service.list_professionals(session)
    await admin_service.record_admin_audit(session, user.id, "list_professionals", resource_type="professional")
    return items


@router.get("/revenue/fines", response_model=List[FineRead])
async def list_fines(session: AsyncSession = Depends(get_session), user=Depends(require_role(Role.GOVERNMENT))):
    items = await admin_service.list_fines(session)
    await admin_service.record_admin_audit(session, user.id, "list_fines", resource_type="fine")
    return items


@router.post("/revenue/fines", response_model=FineRead)
async def create_fine(payload: FineCreate, session: AsyncSession = Depends(get_session), user=Depends(require_role(Role.GOVERNMENT))):
    fine = await admin_service.create_fine(session, payload.project_id, payload.amount, user.id, notes=payload.notes)
    await admin_service.record_admin_audit(session, user.id, "create_fine", resource_type="fine", resource_id=fine.id, details={"project_id": payload.project_id, "amount": payload.amount})
    return fine


@router.get("/revenue/stats", response_model=RevenueStats)
async def revenue_stats(session: AsyncSession = Depends(get_session), user=Depends(require_role(Role.GOVERNMENT))):
    stats = await admin_service.revenue_stats(session)
    await admin_service.record_admin_audit(session, user.id, "view_revenue_stats", resource_type="revenue")
    return stats


@router.post("/policy/archive")
async def archive_policy(payload: PolicyArchiveRequest, session: AsyncSession = Depends(get_session), user=Depends(require_role(Role.GOVERNMENT))):
    try:
        policy = await admin_service.archive_policy(session, payload.policy_id, user.id, reason=payload.reason)
        await admin_service.record_admin_audit(session, user.id, "archive_policy", resource_type="policy", resource_id=policy.id, details={"reason": payload.reason})
        return {"ok": True, "policy_id": policy.id}
    except ValueError:
        raise HTTPException(status_code=404, detail="policy not found")


@router.get("/admin/ai-config", response_model=AdminAIConfigRead)
async def get_ai_config(session: AsyncSession = Depends(get_session), user=Depends(require_role(Role.GOVERNMENT))):
    cfg = await admin_service.get_admin_ai_config(session)
    if not cfg:
        raise HTTPException(status_code=404, detail="ai config not found")
    await admin_service.record_admin_audit(session, user.id, "get_ai_config", resource_type="admin_ai_config", resource_id=cfg.id)
    return cfg


@router.put("/admin/ai-config", response_model=AdminAIConfigRead)
async def put_ai_config(payload: AdminAIConfigUpdate, session: AsyncSession = Depends(get_session), user=Depends(require_role(Role.GOVERNMENT))):
    cfg = await admin_service.upsert_admin_ai_config(session, payload.config, user.id)
    await admin_service.record_admin_audit(session, user.id, "update_ai_config", resource_type="admin_ai_config", resource_id=cfg.id, details={"config_keys": list(payload.config.keys())})
    return cfg


@router.get("/admin/audit", response_model=List[AuditRecord])
async def list_admin_audit(session: AsyncSession = Depends(get_session), user=Depends(require_role(Role.GOVERNMENT))):
    res = await session.execute(select(AdminAudit).order_by(AdminAudit.created_at.desc()).limit(200))
    audits = res.scalars().all()
    await admin_service.record_admin_audit(session, user.id, "list_admin_audit", resource_type="admin_audit")
    return audits
