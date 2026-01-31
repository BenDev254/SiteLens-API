from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user, require_role
from app.models.user import Role
from app.core.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import Project



router = APIRouter()


@router.get("/projects/list")
async def projects_list(
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    # Role gate
    if user.role not in {Role.CONTRACTOR, Role.GOVERNMENT}:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await session.execute(
        select(Project.id, Project.name).order_by(Project.name)
    )

    rows = result.all()

    return {
        "count": len(rows),
        "projects": [{"id": i, "name": n} for i, n in rows],
    }


@router.get("/resources/list")
async def resources_list(user=Depends(require_role(Role.CONTRACTOR))):
    return {"ok": True, "accessed_by": user.username, "area": "resources"}


@router.get("/research/list")
async def research_list(user=Depends(require_role(Role.CONTRACTOR))):
    return {"ok": True, "accessed_by": user.username, "area": "research"}
