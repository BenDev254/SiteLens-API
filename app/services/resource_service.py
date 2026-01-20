from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.labor import Labor
from app.models.equipment import Equipment
from app.models.logistics import Logistics
from app.models.vendor import Vendor
from app.services.project_service import get_project, check_ownership


# Generic helpers
async def create_labor(session: AsyncSession, payload: dict) -> Labor:
    obj = Labor(**payload)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_labor(session: AsyncSession, project_id: int) -> List[Labor]:
    stmt = select(Labor).where(Labor.project_id == project_id)
    res = await session.execute(stmt)
    return res.scalars().all()


async def update_labor(session: AsyncSession, record_id: int, data: dict) -> Optional[Labor]:
    obj = await session.get(Labor, record_id)
    if not obj:
        return None
    for k, v in data.items():
        setattr(obj, k, v)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_labor(session: AsyncSession, record_id: int) -> bool:
    obj = await session.get(Labor, record_id)
    if not obj:
        return False
    await session.delete(obj)
    await session.commit()
    return True


# Equipment
async def create_equipment(session: AsyncSession, payload: dict) -> Equipment:
    obj = Equipment(**payload)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_equipment(session: AsyncSession, project_id: int) -> List[Equipment]:
    stmt = select(Equipment).where(Equipment.project_id == project_id)
    res = await session.execute(stmt)
    return res.scalars().all()


async def update_equipment(session: AsyncSession, record_id: int, data: dict) -> Optional[Equipment]:
    obj = await session.get(Equipment, record_id)
    if not obj:
        return None
    for k, v in data.items():
        setattr(obj, k, v)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_equipment(session: AsyncSession, record_id: int) -> bool:
    obj = await session.get(Equipment, record_id)
    if not obj:
        return False
    await session.delete(obj)
    await session.commit()
    return True


# Logistics
async def create_logistics(session: AsyncSession, payload: dict) -> Logistics:
    obj = Logistics(**payload)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_logistics(session: AsyncSession, project_id: int) -> List[Logistics]:
    stmt = select(Logistics).where(Logistics.project_id == project_id)
    res = await session.execute(stmt)
    return res.scalars().all()


async def update_logistics(session: AsyncSession, record_id: int, data: dict) -> Optional[Logistics]:
    obj = await session.get(Logistics, record_id)
    if not obj:
        return None
    for k, v in data.items():
        setattr(obj, k, v)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_logistics(session: AsyncSession, record_id: int) -> bool:
    obj = await session.get(Logistics, record_id)
    if not obj:
        return False
    await session.delete(obj)
    await session.commit()
    return True


# Vendors
async def create_vendor(session: AsyncSession, payload: dict) -> Vendor:
    obj = Vendor(**payload)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_vendors(session: AsyncSession, contractor_id: Optional[int] = None) -> List[Vendor]:
    stmt = select(Vendor)
    if contractor_id:
        stmt = stmt.where(Vendor.contractor_id == contractor_id)
    res = await session.execute(stmt)
    return res.scalars().all()


async def update_vendor(session: AsyncSession, record_id: int, data: dict) -> Optional[Vendor]:
    obj = await session.get(Vendor, record_id)
    if not obj:
        return None
    for k, v in data.items():
        setattr(obj, k, v)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_vendor(session: AsyncSession, record_id: int) -> bool:
    obj = await session.get(Vendor, record_id)
    if not obj:
        return False
    await session.delete(obj)
    await session.commit()
    return True
