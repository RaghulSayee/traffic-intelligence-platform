from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_database_session
from app.services.camera import CameraService


DatabaseSession = Annotated[
    AsyncSession,
    Depends(get_database_session),
]


def get_camera_service(
    session: DatabaseSession,
) -> CameraService:
    """Construct a camera service for the current request."""

    return CameraService(session)


CameraServiceDependency = Annotated[
    CameraService,
    Depends(get_camera_service),
]