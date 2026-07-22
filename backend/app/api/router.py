from fastapi import (
    APIRouter,
    Depends,
)

from app.api.auth_dependencies import (
    require_traffic_access,
)
from app.api.routes import (
    violations,
)
from app.api.routes.auth import (
    router as auth_router,
)
from app.api.routes.cameras import (
    router as cameras_router,
)
from app.api.routes.health import (
    router as health_router,
)
from app.api.routes.processing_jobs import (
    router as processing_jobs_router,
)
from app.api.routes.videos import (
    router as videos_router,
)


api_router = APIRouter()

traffic_dependencies = [
    Depends(
        require_traffic_access,
    ),
]

api_router.include_router(
    health_router,
)

api_router.include_router(
    auth_router,
    prefix="/auth",
)

api_router.include_router(
    cameras_router,
    prefix="/cameras",
    dependencies=(traffic_dependencies),
)

api_router.include_router(
    videos_router,
    prefix="/videos",
    dependencies=(traffic_dependencies),
)

api_router.include_router(
    processing_jobs_router,
    prefix="/jobs",
    dependencies=(traffic_dependencies),
)

api_router.include_router(
    violations.router,
    prefix="/violations",
    dependencies=(traffic_dependencies),
)
