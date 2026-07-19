from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from app.api.dependencies import (
    VideoIngestionServiceDependency,
)
from app.core.exceptions import (
    CameraNotFoundError,
    DuplicateVideoError,
    InvalidVideoError,
    UnsupportedVideoError,
    VideoTooLargeError,
)
from app.schemas.processing_job import ProcessingJobRead
from app.schemas.video import (
    VideoRead,
    VideoUploadResponse,
)


router = APIRouter(tags=["Videos"])


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_video(
    service: VideoIngestionServiceDependency,
    file: Annotated[
        UploadFile,
        File(description="Traffic video to process"),
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
    """Upload a video and create its processing job."""

    try:
        video, processing_job = await service.ingest(
            upload=file,
            camera_id=camera_id,
            priority=priority,
        )

    except CameraNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except DuplicateVideoError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except UnsupportedVideoError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc

    except VideoTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc

    except InvalidVideoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return VideoUploadResponse(
        video=VideoRead.model_validate(video),
        processing_job=ProcessingJobRead.model_validate(processing_job),
    )
