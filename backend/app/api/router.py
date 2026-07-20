from fastapi import APIRouter

from app.api.routes.cameras import router as cameras_router
from app.api.routes.health import router as health_router
from app.api.routes.processing_jobs import (
    router as processing_jobs_router,
)
from app.api.routes.videos import router as videos_router
from app.api.routes import violations

api_router = APIRouter()

api_router.include_router(health_router)

api_router.include_router(
    cameras_router,
    prefix="/cameras",
)

api_router.include_router(
    videos_router,
    prefix="/videos",
)

api_router.include_router(
    processing_jobs_router,
    prefix="/jobs",
)

api_router.include_router(
    violations.router,
    prefix="/violations",
)
