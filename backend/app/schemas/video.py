from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import (
    VideoSourceType,
    VideoStatus,
)
from app.schemas.processing_job import ProcessingJobRead


class VideoRead(BaseModel):
    """Public representation of an uploaded video."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    camera_id: UUID | None
    original_filename: str
    storage_key: str
    content_type: str | None
    source_type: VideoSourceType
    status: VideoStatus
    size_bytes: int | None
    duration_seconds: float | None
    frames_per_second: float | None
    frame_count: int | None
    width: int | None
    height: int | None
    checksum_sha256: str | None
    video_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class VideoListResponse(BaseModel):
    """Paginated collection of uploaded videos."""

    items: list[VideoRead]
    total: int
    offset: int
    limit: int


class VideoUploadResponse(BaseModel):
    """Response returned after accepting a video."""

    video: VideoRead
    processing_job: ProcessingJobRead
