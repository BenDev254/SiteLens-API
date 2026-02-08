import logging
import subprocess
from fastapi import FastAPI
# from starlette.middleware.base import BaseHTTPMiddleware
import sys


from app.core.config import settings
from app.core.logging import configure_logging
from app.core.exceptions import register_exception_handlers
from app.middleware import CorrelationIdMiddleware
# from app.core.database import init_db
from fastapi.middleware.cors import CORSMiddleware

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

# Middleware: correlation id
# app.add_middleware(BaseHTTPMiddleware, dispatch=CorrelationIdMiddleware())

app.add_middleware(CorrelationIdMiddleware)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route imports
from app.api.health import router as health_router
from app.api.users import router as users_router
from app.api import admin as admin_router
from app.api import projects as projects_router
from app.api.v1 import auth as auth_router
from app.api.v1 import assessments as v1_assessments
from app.api.v1 import compliance as v1_compliance
from app.api.v1 import projects as v1_projects
from app.api.v1 import research as v1_research
from app.api.v1 import resources as v1_resources
from app.api.v1 import live as v1_live
from app.api.v1 import fl as v1_fl
from app.api.v1 import live_ws as v1_live_ws
from app.api.v1 import safety as v1_safety
from app.api.v1 import doc_assessment as v1_doc_assessment
from app.api.v1 import video_upload as v1_video_upload
from app.api.v1 import video_live as v1_video_live

# Register routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(admin_router.router, prefix="/api/admin", tags=["admin"])
app.include_router(projects_router.router, prefix="/api/projects", tags=["projects"])

# v1 API routes
app.include_router(auth_router.router, prefix="/api/v1", tags=["auth"])
app.include_router(v1_assessments.router, prefix="/api/v1", tags=["assessments"])
app.include_router(v1_compliance.router, prefix="/api/v1", tags=["compliance"])
app.include_router(v1_projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(v1_research.router, prefix="/api/v1", tags=["research"])
app.include_router(v1_resources.router, prefix="/api/v1", tags=["resources"])
app.include_router(v1_live.router, prefix="/api/v1", tags=["live-monitoring"])
app.include_router(v1_fl.router, prefix="/api/v1", tags=["federated-learning"])
app.include_router(v1_live_ws.router, prefix="/api/v1", tags=["live-ws"])
app.include_router(v1_safety.router, prefix="/api/v1", tags=["safety"])
app.include_router(v1_doc_assessment.router, prefix="/api/v1", tags=["safety"])
app.include_router(v1_video_upload.router, prefix="/api/v1", tags=["safety"])
app.include_router(v1_video_live.router, prefix="/api/v1", tags=["safety"])


# Exception handlers
register_exception_handlers(app)


# @app.on_event("startup")
# async def on_startup():
#     logger.info("Starting app", extra={"app": settings.APP_NAME})

#     if settings.MIGRATE_ON_START:
#         logger.info("MIGRATE_ON_START enabled: running migrations")
#         try:
#             # Run alembic upgrade head
#             subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
#             logger.info("Database migration completed")
#         except subprocess.CalledProcessError as e:
#             logger.error(f"Migration failed: {e}")
#             raise

@app.on_event("startup")
async def on_startup():
    logger.info("Starting app", extra={"app": settings.APP_NAME})


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down")
