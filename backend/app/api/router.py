from fastapi import APIRouter

from app.api.routes.cameras import router as cameras_router
from app.api.routes.health import router as health_router


api_router = APIRouter()

api_router.include_router(health_router)

api_router.include_router(
    cameras_router,
    prefix="/cameras",
)