import os
import secrets
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
from app.models.user import User, Role
from app.schemas.admin import ContractorRead
from utils.email import send_contractor_email
from app.core.security import hash_password




import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from passlib.hash import bcrypt
from datetime import datetime
from typing import Optional, Dict, Any
import re




# --- CONTRACTOR UTILITIES ---



IDENTIFIER_REGEX = re.compile(r"^P/NO-(\d+)$")

async def generate_next_contractor_identifier(session: AsyncSession) -> str:
    res = await session.execute(
        select(User.identifier)
        .where(
            User.role == Role.CONTRACTOR,
            User.identifier.is_not(None)
        )
        .order_by(User.id.desc())
    )

    for (identifier,) in res.all():
        match = IDENTIFIER_REGEX.match(identifier)
        if match:
            last_num = int(match.group(1))
            return f"P/NO-{last_num + 1:03d}"

    return "P/NO-001"



async def create_contractor(session: AsyncSession, payload) -> Contractor:
    identifier = await generate_next_contractor_identifier(session)
    raw_password = secrets.token_urlsafe(12)
    hashed_password = hash_password(raw_password)


    user = User(
        username=payload.name.replace(" ", "_"),
        email=payload.email,
        hashed_password=hashed_password,
        role=Role.CONTRACTOR,
        identifier=identifier,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    contractor = Contractor(
        name=payload.name,
        headquarters=payload.headquarters,
        owner_id=user.id,
    )

    session.add(contractor)
    await session.commit()
    await session.refresh(contractor)


    from app.core.config import settings
    print("EMAIL_ADDRESS:", repr(settings.EMAIL_ADDRESS))
    print("EMAIL_PASSWORD:", "SET" if settings.EMAIL_PASSWORD else "MISSING")


    send_contractor_email(
        to_email=payload.email,
        username=user.username,
        password=raw_password,
        identifier=identifier,
    )

    return contractor


async def create_professional(session: AsyncSession, payload) -> Professional:
    # Check contractor exists
    res = await session.execute(select(Contractor).where(Contractor.id == payload.contractor_id))
    contractor = res.scalar_one_or_none()
    if not contractor:
        raise ValueError("Contractor not found")

    # Generate random password
    raw_password = secrets.token_urlsafe(12)
    hashed_password = hash_password(raw_password)


    # Create User for professional
    user = User(
        username=payload.name.replace(" ", "_"),
        hashed_password=hashed_password,
        role=Role.CONTRACTOR,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Create Professional record
    professional = Professional(
        name=payload.name,
        title=payload.title,
        contractor_id=contractor.id,
    )
    session.add(professional)
    await session.commit()
    await session.refresh(professional)

    
    # Get the contractor's user identifier
    contractor_user = await session.get(User, contractor.owner_id)

    # Send email
    if getattr(payload, "email", None):
        send_contractor_email(
            to_email=payload.email,
            username=user.username,
            password=raw_password,
            identifier=contractor_user.identifier  # <-- pass the identifier
        )


    return professional


# --- DELETE & LIST FUNCTIONS ---

async def delete_contractor(session: AsyncSession, contractor_id: int):
    res = await session.execute(select(Contractor).where(Contractor.id == contractor_id))
    contractor = res.scalar_one_or_none()
    if not contractor:
        raise ValueError("Contractor not found")
    await session.delete(contractor)
    await session.commit()


async def delete_professional(session: AsyncSession, professional_id: int):
    res = await session.execute(select(Professional).where(Professional.id == professional_id))
    professional = res.scalar_one_or_none()
    if not professional:
        raise ValueError("Professional not found")
    await session.delete(professional)
    await session.commit()




async def list_contractors(session: AsyncSession):
    stmt = (
        select(Contractor)
        .options(selectinload(Contractor.owner))
    )
    res = await session.execute(stmt)
    contractors = res.scalars().all()

    return [
        ContractorRead(
            id=c.id,
            name=c.name,
            headquarters=c.headquarters,
            email=c.owner.username if c.owner else None,
            identifier=c.owner.identifier if c.owner else None,
        )
        for c in contractors
    ]






async def list_professionals(session: AsyncSession):
    res = await session.execute(select(Professional))
    professionals = res.scalars().all()
    for p in professionals:
        res_user = await session.execute(select(User).where(User.username == p.name.replace(" ", "_")))
        user = res_user.scalar_one_or_none()
        if user:
            p.email = user.username
    return professionals


# --- ADMIN AUDIT ---

async def record_admin_audit(session: AsyncSession, user_id: Optional[int], action: str, resource_type: Optional[str] = None,
                             resource_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None) -> AdminAudit:
    audit = AdminAudit(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details
    )
    session.add(audit)
    await session.commit()
    await session.refresh(audit)
    return audit



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
