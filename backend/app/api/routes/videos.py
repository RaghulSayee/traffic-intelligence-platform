from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)

from app.api.dependencies import (
    VideoIngestionServiceDependency,
    VideoQueryServiceDependency,
)
from app.core.exceptions import (
    CameraNotFoundError,
    DuplicateVideoError,
    InvalidVideoError,
    UnsupportedVideoError,
    VideoTooLargeError,
    VideoNotFoundError,
)
from app.models.enums import VideoStatus
from app.schemas.processing_job import (
    ProcessingJobRead,
)
from app.schemas.video import (
    VideoListResponse,
    VideoRead,
    VideoUploadResponse,
)


router = APIRouter(tags=["Videos"])


@router.get(
    "",
    response_model=VideoListResponse,
)
async def list_videos(
    service: VideoQueryServiceDependency,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 20,
    video_status: Annotated[
        VideoStatus | None,
        Query(alias="status"),
    ] = None,
    camera_id: Annotated[
        UUID | None,
        Query(),
    ] = None,
) -> VideoListResponse:
    """Return uploaded videos using filters."""

    videos, total = await service.list_videos(
        offset=offset,
        limit=limit,
        status=video_status,
        camera_id=camera_id,
    )

    return VideoListResponse(
        items=[VideoRead.model_validate(video) for video in videos],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_video(
    service: VideoIngestionServiceDependency,
    file: Annotated[
        UploadFile,
        File(description=("Traffic video to process")),
    ],
    camera_id: Annotated[
        UUID | None,
        Form(),
    ] = None,
    priority: Annotated[
        int,
        Form(ge=-10, le=10),
    ] = 0,
) -> VideoUploadResponse:
    """Upload a video and create its job."""

    try:
        video, processing_job = await service.ingest(
            upload=file,
            camera_id=camera_id,
            priority=priority,
        )

    except CameraNotFoundError as exc:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=str(exc),
        ) from exc

    except DuplicateVideoError as exc:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=str(exc),
        ) from exc

    except UnsupportedVideoError as exc:
        raise HTTPException(
            status_code=(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
            detail=str(exc),
        ) from exc

    except VideoTooLargeError as exc:
        raise HTTPException(
            status_code=(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE),
            detail=str(exc),
        ) from exc

    except InvalidVideoError as exc:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
            detail=str(exc),
        ) from exc

    return VideoUploadResponse(
        video=VideoRead.model_validate(video),
        processing_job=(ProcessingJobRead.model_validate(processing_job)),
    )


@router.delete(
    "/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_video(
    video_id: UUID,
    service: VideoQueryServiceDependency,
) -> Response:
    """Delete a video and all related processing data."""

    try:
        await service.delete_video(video_id)

    except VideoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
