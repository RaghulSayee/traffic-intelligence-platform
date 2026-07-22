from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WorkerLostLeaseError
from app.models.enums import (
    ProcessingJobStatus,
    VideoStatus,
)
from app.models.processing_job import ProcessingJob
from app.models.video import Video


class ProcessingJobRepository:
    """Perform persistence and worker-queue operations."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create(
        self,
        processing_job: ProcessingJob,
    ) -> ProcessingJob:
        self.session.add(processing_job)
        await self.session.flush()

        return processing_job

    async def get_by_id(
        self,
        job_id: UUID,
    ) -> ProcessingJob | None:
        return await self.session.get(
            ProcessingJob,
            job_id,
        )

    async def list_jobs(
        self,
        *,
        offset: int,
        limit: int,
        status: ProcessingJobStatus | None,
        video_id: UUID | None,
    ) -> tuple[list[ProcessingJob], int]:
        """Return processing jobs using filters."""

        filters = []

        if status is not None:
            filters.append(ProcessingJob.status == status)

        if video_id is not None:
            filters.append(ProcessingJob.video_id == video_id)

        count_statement = select(func.count()).select_from(ProcessingJob)

        list_statement = (
            select(ProcessingJob)
            .order_by(ProcessingJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if filters:
            count_statement = count_statement.where(*filters)

            list_statement = list_statement.where(*filters)

        count_result = await self.session.execute(count_statement)

        list_result = await self.session.execute(list_statement)

        total = int(count_result.scalar_one())

        jobs = list(list_result.scalars().all())

        return jobs, total

    async def recover_expired_jobs(
        self,
        *,
        maximum_attempts: int,
        batch_size: int,
    ) -> int:
        """
        Requeue or fail running jobs whose worker lease expired.
        """

        now = datetime.now(timezone.utc)

        statement = (
            select(ProcessingJob)
            .where(
                ProcessingJob.status == ProcessingJobStatus.RUNNING,
                ProcessingJob.lease_expires_at.is_not(None),
                ProcessingJob.lease_expires_at < now,
            )
            .order_by(ProcessingJob.lease_expires_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )

        result = await self.session.execute(statement)
        jobs = list(result.scalars().all())

        for job in jobs:
            video = await self.session.get(
                Video,
                job.video_id,
            )

            if job.attempt_count >= maximum_attempts:
                job.status = ProcessingJobStatus.FAILED
                job.completed_at = now
                job.error_message = (
                    "Worker lease expired after the maximum number of attempts."
                )

                if video is not None:
                    video.status = VideoStatus.FAILED

            else:
                job.status = ProcessingJobStatus.QUEUED
                job.progress_percent = 0.0
                job.last_processed_frame = 0
                job.error_message = (
                    "Previous worker lease expired. The job was returned to the queue."
                )

                if video is not None:
                    video.status = VideoStatus.QUEUED

            job.worker_id = None
            job.claimed_at = None
            job.heartbeat_at = None
            job.lease_expires_at = None

        if jobs:
            await self.session.commit()
        else:
            await self.session.rollback()

        return len(jobs)

    async def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int,
        maximum_attempts: int,
    ) -> ProcessingJob | None:
        """Atomically claim the highest-priority queued job."""

        now = datetime.now(timezone.utc)

        statement = (
            select(ProcessingJob)
            .where(
                ProcessingJob.status == ProcessingJobStatus.QUEUED,
                ProcessingJob.attempt_count < maximum_attempts,
            )
            .order_by(
                ProcessingJob.priority.desc(),
                ProcessingJob.created_at.asc(),
            )
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        result = await self.session.execute(statement)
        job = result.scalar_one_or_none()

        if job is None:
            await self.session.rollback()
            return None

        video = await self.session.get(
            Video,
            job.video_id,
        )

        job.status = ProcessingJobStatus.RUNNING
        job.worker_id = worker_id
        job.claimed_at = now
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        job.attempt_count += 1
        job.progress_percent = 0.0
        job.last_processed_frame = 0
        job.error_message = None

        if job.started_at is None:
            job.started_at = now

        if video is not None:
            video.status = VideoStatus.PROCESSING

        await self.session.commit()
        await self.session.refresh(job)

        return job

    async def update_progress(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        progress_percent: float,
        last_processed_frame: int,
        pipeline_version: str,
        metrics: dict[str, Any],
        lease_seconds: int,
    ) -> None:
        """Persist progress while extending worker ownership."""

        job = await self._get_owned_running_job(
            job_id=job_id,
            worker_id=worker_id,
        )

        now = datetime.now(timezone.utc)

        job.progress_percent = min(
            max(progress_percent, 0.0),
            99.0,
        )

        job.last_processed_frame = max(
            last_processed_frame,
            0,
        )

        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)

        job.pipeline_version = pipeline_version

        job.job_metrics = {
            **(job.job_metrics or {}),
            **metrics,
        }

        await self.session.commit()

    async def mark_succeeded(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        pipeline_version: str,
        metrics: dict[str, Any],
    ) -> None:
        """Mark a worker-owned job as successfully completed."""

        job = await self._get_owned_running_job(
            job_id=job_id,
            worker_id=worker_id,
        )

        now = datetime.now(timezone.utc)

        video = await self.session.get(
            Video,
            job.video_id,
        )

        job.status = ProcessingJobStatus.SUCCEEDED
        job.progress_percent = 100.0
        job.completed_at = now
        job.heartbeat_at = now
        job.lease_expires_at = None
        job.error_message = None
        job.pipeline_version = pipeline_version

        job.job_metrics = {
            **(job.job_metrics or {}),
            **metrics,
        }

        if video is not None:
            video.status = VideoStatus.COMPLETED

        await self.session.commit()

    async def mark_failed_or_retry(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        error_message: str,
        maximum_attempts: int,
    ) -> ProcessingJobStatus:
        """Retry a failed attempt or permanently fail the job."""

        job = await self._get_owned_running_job(
            job_id=job_id,
            worker_id=worker_id,
        )

        now = datetime.now(timezone.utc)

        video = await self.session.get(
            Video,
            job.video_id,
        )

        job.error_message = error_message[:4000]
        job.heartbeat_at = now
        job.lease_expires_at = None

        if job.attempt_count < maximum_attempts:
            job.status = ProcessingJobStatus.QUEUED
            job.progress_percent = 0.0
            job.last_processed_frame = 0
            job.worker_id = None
            job.claimed_at = None
            job.heartbeat_at = None

            if video is not None:
                video.status = VideoStatus.QUEUED

        else:
            job.status = ProcessingJobStatus.FAILED
            job.completed_at = now

            if video is not None:
                video.status = VideoStatus.FAILED

        await self.session.commit()

        return job.status

    async def _get_owned_running_job(
        self,
        *,
        job_id: UUID,
        worker_id: str,
    ) -> ProcessingJob:
        """Lock and return a running job owned by this worker."""

        statement = (
            select(ProcessingJob)
            .where(
                and_(
                    ProcessingJob.id == job_id,
                    ProcessingJob.worker_id == worker_id,
                    ProcessingJob.status == ProcessingJobStatus.RUNNING,
                )
            )
            .with_for_update()
        )

        result = await self.session.execute(statement)
        job = result.scalar_one_or_none()

        if job is None:
            await self.session.rollback()
            raise WorkerLostLeaseError(job_id)

        return job
