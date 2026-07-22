import asyncio
import shutil
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import VideoNotFoundError
from app.models.enums import (
    ProcessingJobStatus,
    VideoStatus,
)
from app.models.video import Video
from app.repositories.video import VideoRepository
from app.storage.base import VideoStorage


class VideoQueryService:
    """Provide video query and deletion operations."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        storage: VideoStorage,
        evidence_root: Path,
    ) -> None:
        self.session = session
        self.repository = VideoRepository(session)
        self.storage = storage
        self.evidence_root = evidence_root.resolve()

    async def list_videos(
        self,
        *,
        offset: int,
        limit: int,
        status: VideoStatus | None,
        camera_id: UUID | None,
    ) -> tuple[list[Video], int]:
        """Return a filtered video collection."""

        return await self.repository.list_videos(
            offset=offset,
            limit=limit,
            status=status,
            camera_id=camera_id,
        )

    async def delete_video(
        self,
        video_id: UUID,
    ) -> None:
        """Delete a completed video, related records and stored files."""

        video = await self.repository.get_by_id_for_delete(video_id)

        if video is None:
            raise VideoNotFoundError(video_id)

        active_statuses = {
            ProcessingJobStatus.QUEUED,
            ProcessingJobStatus.RUNNING,
        }

        active_jobs = [
            job for job in video.processing_jobs if job.status in active_statuses
        ]

        if active_jobs:
            raise ValueError(
                "A video cannot be deleted while one of its "
                "processing jobs is queued or running."
            )

        storage_key = video.storage_key

        job_ids = [job.id for job in video.processing_jobs]

        try:
            await self.repository.delete(video)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        # Remove the original uploaded video.
        await self.storage.delete(storage_key)

        # Remove previews, summaries, detections and evidence.
        for job_id in job_ids:
            artifact_directory = self.evidence_root / str(job_id)

            temporary_directory = self.evidence_root / f".{job_id}.part"

            await asyncio.to_thread(
                shutil.rmtree,
                artifact_directory,
                ignore_errors=True,
            )

            await asyncio.to_thread(
                shutil.rmtree,
                temporary_directory,
                ignore_errors=True,
            )
