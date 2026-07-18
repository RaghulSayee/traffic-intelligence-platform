from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Response,
    status as http_status,
)

from app.api.dependencies import CameraServiceDependency
from app.core.exceptions import (
    CameraNameConflictError,
    CameraNotFoundError,
)
from app.models.enums import CameraStatus
from app.schemas.camera import (
    CameraCreate,
    CameraListResponse,
    CameraRead,
    CameraUpdate,
)


router = APIRouter(
    tags=["Cameras"],
)


@router.post(
    "",
    response_model=CameraRead,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_camera(
    payload: CameraCreate,
    service: CameraServiceDependency,
) -> CameraRead:
    """Register a traffic-monitoring camera."""

    try:
        camera = await service.create_camera(payload)
    except CameraNameConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return CameraRead.model_validate(camera)


@router.get(
    "",
    response_model=CameraListResponse,
)
async def list_cameras(
    service: CameraServiceDependency,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 20,
    camera_status: Annotated[
        CameraStatus | None,
        Query(alias="status"),
    ] = None,
) -> CameraListResponse:
    """Return registered cameras using pagination."""

    cameras, total = await service.list_cameras(
        offset=offset,
        limit=limit,
        camera_status=camera_status,
    )

    return CameraListResponse(
        items=[
            CameraRead.model_validate(camera)
            for camera in cameras
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{camera_id}",
    response_model=CameraRead,
)
async def get_camera(
    camera_id: UUID,
    service: CameraServiceDependency,
) -> CameraRead:
    """Return one camera using its UUID."""

    try:
        camera = await service.get_camera(camera_id)
    except CameraNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return CameraRead.model_validate(camera)


@router.patch(
    "/{camera_id}",
    response_model=CameraRead,
)
async def update_camera(
    camera_id: UUID,
    payload: CameraUpdate,
    service: CameraServiceDependency,
) -> CameraRead:
    """Partially update an existing camera."""

    try:
        camera = await service.update_camera(
            camera_id,
            payload,
        )
    except CameraNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CameraNameConflictError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return CameraRead.model_validate(camera)


@router.delete(
    "/{camera_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
)
async def delete_camera(
    camera_id: UUID,
    service: CameraServiceDependency,
) -> Response:
    """Delete an existing camera."""

    try:
        await service.delete_camera(camera_id)
    except CameraNotFoundError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response(
        status_code=http_status.HTTP_204_NO_CONTENT
    )