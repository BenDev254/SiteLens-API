from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str = "ok"


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Simple health check endpoint."""
    return HealthResponse()
