from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_database_session
from app.services.camera import CameraService

from functools import lru_cache

from app.core.config import get_settings
from app.media.metadata import (
    OpenCVVideoMetadataExtractor,
    VideoMetadataExtractor,
)
from app.services.processing_job import ProcessingJobService
from app.services.video_ingestion import VideoIngestionService
from app.storage.base import VideoStorage
from app.storage.local import LocalVideoStorage
from app.services.violation_event import (
    ViolationEventService,
)

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


@lru_cache
def get_video_storage() -> VideoStorage:
    """Create the configured video-storage provider."""

    settings = get_settings()

    return LocalVideoStorage(
        root=settings.video_storage_path,
        maximum_bytes=settings.max_video_upload_bytes,
        chunk_size_bytes=settings.upload_chunk_size_bytes,
    )


@lru_cache
def get_video_metadata_extractor() -> VideoMetadataExtractor:
    """Create the configured video metadata extractor."""

    return OpenCVVideoMetadataExtractor()


def get_video_ingestion_service(
    session: DatabaseSession,
) -> VideoIngestionService:
    return VideoIngestionService(
        session=session,
        storage=get_video_storage(),
        metadata_extractor=get_video_metadata_extractor(),
    )


VideoIngestionServiceDependency = Annotated[
    VideoIngestionService,
    Depends(get_video_ingestion_service),
]


def get_processing_job_service(
    session: DatabaseSession,
) -> ProcessingJobService:
    return ProcessingJobService(session)


ProcessingJobServiceDependency = Annotated[
    ProcessingJobService,
    Depends(get_processing_job_service),
]


def get_violation_event_service(
    session: DatabaseSession,
) -> ViolationEventService:
    """Construct the violation service for a request."""

    return ViolationEventService(session)


ViolationEventServiceDependency = Annotated[
    ViolationEventService,
    Depends(get_violation_event_service),
]
