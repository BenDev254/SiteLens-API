from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contractor import Contractor
from app.models.professional import Professional
from app.models.fine import Fine
from app.models.financial_telemetry import FinancialTelemetry
from app.models.policy import Policy
from app.models.admin_ai_config import AdminAIConfig
from app.models.admin_audit import AdminAudit
from app.models.project import Project


async def record_admin_audit(session: AsyncSession, user_id: Optional[int], action: str, resource_type: Optional[str] = None, resource_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None) -> AdminAudit:
    audit = AdminAudit(user_id=user_id, action=action, resource_type=resource_type, resource_id=resource_id, details=details)
    session.add(audit)
    await session.commit()
    await session.refresh(audit)
    return audit


async def list_contractors(session: AsyncSession) -> List[Contractor]:
    stmt = select(Contractor)
    res = await session.execute(stmt)
    return res.scalars().all()


async def list_professionals(session: AsyncSession) -> List[Professional]:
    stmt = select(Professional)
    res = await session.execute(stmt)
    return res.scalars().all()


async def list_fines(session: AsyncSession) -> List[Fine]:
    stmt = select(Fine)
    res = await session.execute(stmt)
    return res.scalars().all()


async def create_fine(session: AsyncSession, project_id: Optional[int], amount: float, issued_by: Optional[int], notes: Optional[str] = None) -> Fine:
    # Validate that project exists if project_id is provided
    if project_id and project_id > 0:
        project = await session.get(Project, project_id)
        if not project:
            raise ValueError(f"Project with id {project_id} not found")
    
    fine = Fine(project_id=project_id if project_id and project_id > 0 else None, amount=amount, issued_by=issued_by, notes=notes)
    session.add(fine)
    await session.commit()
    await session.refresh(fine)
    return fine


async def revenue_stats(session: AsyncSession) -> Dict[str, Any]:
    # total revenue from FinancialTelemetry.amount
    stmt = select(func.coalesce(func.sum(FinancialTelemetry.amount), 0.0))
    total_revenue = float((await session.execute(stmt)).scalar() or 0.0)

    stmt2 = select(func.coalesce(func.sum(Fine.amount), 0.0))
    total_fines = float((await session.execute(stmt2)).scalar() or 0.0)

    stmt3 = select(func.count(func.distinct(FinancialTelemetry.project_id)))
    total_projects = int((await session.execute(stmt3)).scalar() or 0)

    avg = (total_revenue / total_projects) if total_projects > 0 else None

    return {
        "total_revenue": total_revenue,
        "total_fines": total_fines,
        "total_projects": total_projects,
        "avg_revenue_per_project": avg,
    }


async def archive_policy(session: AsyncSession, policy_id: int, user_id: Optional[int], reason: Optional[str] = None) -> Policy:
    p = await session.get(Policy, policy_id)
    if not p:
        raise ValueError("policy not found")
    p.archived = True
    p.archived_at = datetime.utcnow()
    p.archived_by = user_id
    session.add(p)
    await session.commit()
    await session.refresh(p)
    # record audit elsewhere
    return p


async def get_admin_ai_config(session: AsyncSession) -> Optional[AdminAIConfig]:
    stmt = select(AdminAIConfig).order_by(AdminAIConfig.updated_at.desc()).limit(1)
    res = await session.execute(stmt)
    return res.scalars().first()


async def upsert_admin_ai_config(session: AsyncSession, config: Dict[str, Any], user_id: Optional[int]) -> AdminAIConfig:
    existing = await get_admin_ai_config(session)
    if existing:
        existing.config = config
        existing.updated_at = datetime.utcnow()
        existing.updated_by = user_id
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return existing
    new = AdminAIConfig(config=config, updated_by=user_id)
    session.add(new)
    await session.commit()
    await session.refresh(new)
    return new
