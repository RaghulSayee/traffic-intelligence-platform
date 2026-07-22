from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ProcessingJobStatus


class ProcessingJobRead(BaseModel):
    """Public representation of a processing job."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    status: ProcessingJobStatus
    progress_percent: float
    priority: int
    attempt_count: int
    last_processed_frame: int

    pipeline_name: str
    pipeline_version: str | None

    worker_id: str | None
    claimed_at: datetime | None
    heartbeat_at: datetime | None
    lease_expires_at: datetime | None

    model_versions: dict[str, Any]
    job_metrics: dict[str, Any]

    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None

    created_at: datetime
    updated_at: datetime


class ProcessingJobListResponse(BaseModel):
    """Paginated collection of processing jobs."""

    items: list[ProcessingJobRead]
    total: int
    offset: int
    limit: int
