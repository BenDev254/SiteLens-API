from fastapi import APIRouter, Depends
from app.core.security import require_role
from app.models.user import Role

router = APIRouter()


@router.get("/projects/list")
async def projects_list(user=Depends(require_role(Role.CONTRACTOR))):
    return {"ok": True, "accessed_by": user.username, "area": "projects"}


@router.get("/resources/list")
async def resources_list(user=Depends(require_role(Role.CONTRACTOR))):
    return {"ok": True, "accessed_by": user.username, "area": "resources"}


@router.get("/research/list")
async def research_list(user=Depends(require_role(Role.CONTRACTOR))):
    return {"ok": True, "accessed_by": user.username, "area": "research"}
