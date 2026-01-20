from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user
from app.models.contractor import Contractor
from app.services.resource_service import (
    create_labor, list_labor, update_labor, delete_labor,
    create_equipment, list_equipment, update_equipment, delete_equipment,
    create_logistics, list_logistics, update_logistics, delete_logistics,
    create_vendor, list_vendors, update_vendor, delete_vendor,
)
from app.schemas.resources import (
    LaborCreate, LaborRead, EquipmentCreate, EquipmentRead,
    LogisticsCreate, LogisticsRead, VendorCreate, VendorRead, ListResponse,
)
from app.services.project_service import get_project, check_ownership

router = APIRouter(prefix="/resources", tags=["resources"]) 


# Labor endpoints
@router.post("/labor", response_model=LaborRead, status_code=status.HTTP_201_CREATED)
async def add_labor(payload: LaborCreate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    obj = await create_labor(session, payload.model_dump())
    return LaborRead(**obj.model_dump())


@router.get("/labor", response_model=ListResponse)
async def get_labor(project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    items = await list_labor(session, project_id)
    return ListResponse(items=[LaborRead(**i.model_dump()) for i in items], total=len(items))


@router.put("/labor/{record_id}", response_model=LaborRead)
async def put_labor(record_id: int, payload: LaborCreate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    # ensure ownership via project
    project = await get_project(session, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    obj = await update_labor(session, record_id, payload.model_dump())
    if not obj:
        raise HTTPException(status_code=404, detail="Record not found")
    return LaborRead(**obj.model_dump())


@router.delete("/labor/{record_id}")
async def del_labor(record_id: int, project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    ok = await delete_labor(session, record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"ok": True}


# Equipment endpoints
@router.post("/equipment", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
async def add_equipment(payload: EquipmentCreate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    obj = await create_equipment(session, payload.model_dump())
    return EquipmentRead(**obj.model_dump())


@router.get("/equipment", response_model=ListResponse)
async def get_equipment(project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    items = await list_equipment(session, project_id)
    return ListResponse(items=[EquipmentRead(**i.model_dump()) for i in items], total=len(items))


@router.put("/equipment/{record_id}", response_model=EquipmentRead)
async def put_equipment(record_id: int, payload: EquipmentCreate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    obj = await update_equipment(session, record_id, payload.model_dump())
    if not obj:
        raise HTTPException(status_code=404, detail="Record not found")
    return EquipmentRead(**obj.model_dump())


@router.delete("/equipment/{record_id}")
async def del_equipment(record_id: int, project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    ok = await delete_equipment(session, record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"ok": True}


# Logistics endpoints
@router.post("/logistics", response_model=LogisticsRead, status_code=status.HTTP_201_CREATED)
async def add_logistics(payload: LogisticsCreate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    obj = await create_logistics(session, payload.model_dump())
    return LogisticsRead(**obj.model_dump())


@router.get("/logistics", response_model=ListResponse)
async def get_logistics(project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    items = await list_logistics(session, project_id)
    return ListResponse(items=[LogisticsRead(**i.model_dump()) for i in items], total=len(items))


@router.put("/logistics/{record_id}", response_model=LogisticsRead)
async def put_logistics(record_id: int, payload: LogisticsCreate, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    obj = await update_logistics(session, record_id, payload.model_dump())
    if not obj:
        raise HTTPException(status_code=404, detail="Record not found")
    return LogisticsRead(**obj.model_dump())


@router.delete("/logistics/{record_id}")
async def del_logistics(record_id: int, project_id: int, session: AsyncSession = Depends(get_session), user=Depends(get_current_user)):
    project = await get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not await check_ownership(session, project, user):
        raise HTTPException(status_code=403, detail="Not owner")
    ok = await delete_logistics(session, record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"ok": True}


# Vendors (list/create available; vendor creation limited to contractor owners)
@router.post(
    "/vendors",
    response_model=VendorRead,
    status_code=status.HTTP_201_CREATED
)
async def add_vendor(
    payload: VendorCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    contractor = None

    if payload.contractor_id is not None:
        contractor = await session.get(Contractor, payload.contractor_id)

        if not contractor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid contractor_id"
            )

        if contractor.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this contractor"
            )

    vendor = await create_vendor(
        session,
        {
            "name": payload.name,
            "contact_name": payload.contact_name,
            "contact_email": payload.contact_email,
            "contractor_id": contractor.id if contractor else None,
        },
    )

    return VendorRead(**vendor.model_dump())



@router.get("/vendors", response_model=ListResponse)
async def get_vendors(
    contractor_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    if contractor_id is not None:
        contractor = await session.get(Contractor, contractor_id)

        if not contractor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid contractor_id"
            )

        if contractor.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this contractor"
            )

    items = await list_vendors(session, contractor_id)

    return ListResponse(
        items=[VendorRead(**i.model_dump()) for i in items],
        total=len(items),
    )

