import asyncio
import logging
import time
from pathlib import Path
from uuid import UUID

import cv2

from app.core.config import Settings
from app.core.exceptions import (
    InvalidVideoError,
    WorkerLostLeaseError,
)
from app.db.session import AsyncSessionFactory
from app.models.processing_job import ProcessingJob
from app.models.video import Video
from app.pipelines.base import (
    FramePacket,
    VideoContext,
)
from app.pipelines.factory import create_video_pipeline
from app.repositories.processing_job import (
    ProcessingJobRepository,
)
from app.storage.base import VideoStorage


logger = logging.getLogger(__name__)


class VideoProcessingWorker:
    """Poll, claim and process queued traffic videos."""

    def __init__(
        self,
        *,
        worker_id: str,
        settings: Settings,
        storage: VideoStorage,
        stop_event: asyncio.Event,
    ) -> None:
        self.worker_id = worker_id
        self.settings = settings
        self.storage = storage
        self.stop_event = stop_event

    async def run_forever(self) -> None:
        """Continuously recover and process queued jobs."""

        logger.info(
            "Worker started: %s",
            self.worker_id,
        )

        while not self.stop_event.is_set():
            try:
                await self._recover_expired_jobs()

                job_id = await self._claim_next_job()

                if job_id is None:
                    await self._wait_for_next_poll()
                    continue

                await self._process_job(job_id)

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception("Unexpected error in worker loop.")

                await self._wait_for_next_poll()

        logger.info(
            "Worker stopped: %s",
            self.worker_id,
        )

    async def _recover_expired_jobs(self) -> None:
        async with AsyncSessionFactory() as session:
            repository = ProcessingJobRepository(session)

            recovered = await repository.recover_expired_jobs(
                maximum_attempts=(self.settings.worker_max_attempts),
                batch_size=(self.settings.worker_recovery_batch_size),
            )

        if recovered:
            logger.warning(
                "Recovered %s expired processing job(s).",
                recovered,
            )

    async def _claim_next_job(self) -> UUID | None:
        async with AsyncSessionFactory() as session:
            repository = ProcessingJobRepository(session)

            job = await repository.claim_next(
                worker_id=self.worker_id,
                lease_seconds=(self.settings.worker_lease_seconds),
                maximum_attempts=(self.settings.worker_max_attempts),
            )

        if job is None:
            return None

        logger.info(
            "Claimed job %s on attempt %s.",
            job.id,
            job.attempt_count,
        )

        return job.id

    async def _process_job(
        self,
        job_id: UUID,
    ) -> None:
        try:
            job, video = await self._load_job_and_video(job_id)

            path = self.storage.resolve_path(video.storage_key)

            await self._decode_and_process(
                job=job,
                video=video,
                path=path,
            )

        except WorkerLostLeaseError:
            logger.warning(
                "Worker %s lost ownership of job %s.",
                self.worker_id,
                job_id,
            )

        except Exception as exc:
            logger.exception(
                "Job %s failed during processing.",
                job_id,
            )

            try:
                await self._record_failure(
                    job_id=job_id,
                    error_message=(f"{type(exc).__name__}: {exc}"),
                )

            except WorkerLostLeaseError:
                logger.warning(
                    "Could not record failure because job %s "
                    "is now owned by another worker.",
                    job_id,
                )

    async def _load_job_and_video(
        self,
        job_id: UUID,
    ) -> tuple[ProcessingJob, Video]:
        async with AsyncSessionFactory() as session:
            job = await session.get(
                ProcessingJob,
                job_id,
            )

            if job is None:
                raise RuntimeError(f"Processing job '{job_id}' disappeared.")

            video = await session.get(
                Video,
                job.video_id,
            )

            if video is None:
                raise RuntimeError(f"Video '{job.video_id}' disappeared.")

            session.expunge(job)
            session.expunge(video)

            return job, video

    async def _decode_and_process(
        self,
        *,
        job: ProcessingJob,
        video: Video,
        path: Path,
    ) -> None:
        pipeline = create_video_pipeline(job.pipeline_name)

        capture = cv2.VideoCapture(str(path))

        if not capture.isOpened():
            raise InvalidVideoError("The worker could not open the stored video.")

        processed_frames = 0
        latest_metrics: dict[str, float] = {}

        started_clock = time.perf_counter()

        expected_frame_count = video.frame_count or self._positive_integer(
            capture.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        fps = video.frames_per_second or self._positive_float(
            capture.get(cv2.CAP_PROP_FPS)
        )

        pipeline.start(
            VideoContext(
                video_id=str(video.id),
                width=video.width or 0,
                height=video.height or 0,
                frames_per_second=fps,
                expected_frame_count=expected_frame_count,
            )
        )

        try:
            while not self.stop_event.is_set():
                successful_read, frame = capture.read()

                if not successful_read:
                    break

                processed_frames += 1

                timestamp_seconds = self._timestamp_seconds(
                    capture=capture,
                    frame_number=processed_frames,
                    frames_per_second=fps,
                )

                analysis = pipeline.process_frame(
                    FramePacket(
                        frame_number=processed_frames,
                        timestamp_seconds=timestamp_seconds,
                        image=frame,
                    )
                )

                latest_metrics = analysis.metrics

                should_report = (
                    processed_frames % self.settings.worker_progress_interval_frames
                    == 0
                )

                is_final_expected_frame = (
                    expected_frame_count is not None
                    and processed_frames >= expected_frame_count
                )

                if should_report or is_final_expected_frame:
                    await self._report_progress(
                        job_id=job.id,
                        processed_frames=processed_frames,
                        expected_frame_count=(expected_frame_count),
                        started_clock=started_clock,
                        latest_metrics=latest_metrics,
                        pipeline_name=pipeline.name,
                        pipeline_version=pipeline.version,
                    )

            if processed_frames == 0:
                raise InvalidVideoError("The worker did not decode any frames.")

            summary = pipeline.finish()

            elapsed_seconds = max(
                time.perf_counter() - started_clock,
                0.000001,
            )

            final_metrics = {
                "pipeline_name": pipeline.name,
                "pipeline_version": pipeline.version,
                "processed_frames": processed_frames,
                "processing_seconds": elapsed_seconds,
                "average_processing_fps": (processed_frames / elapsed_seconds),
                "latest_frame_metrics": latest_metrics,
                "summary": summary.metrics,
            }

            await self._mark_succeeded(
                job_id=job.id,
                metrics=final_metrics,
            )

            logger.info(
                "Completed job %s: %s frames in %.2f seconds.",
                job.id,
                processed_frames,
                elapsed_seconds,
            )

        finally:
            capture.release()

    async def _report_progress(
        self,
        *,
        job_id: UUID,
        processed_frames: int,
        expected_frame_count: int | None,
        started_clock: float,
        latest_metrics: dict[str, float],
        pipeline_name: str,
        pipeline_version: str,
    ) -> None:
        elapsed_seconds = max(
            time.perf_counter() - started_clock,
            0.000001,
        )

        if expected_frame_count:
            progress_percent = min(
                processed_frames / expected_frame_count * 100.0,
                99.0,
            )
        else:
            progress_percent = 0.0

        metrics = {
            "processed_frames": processed_frames,
            "expected_frame_count": expected_frame_count,
            "current_processing_fps": (processed_frames / elapsed_seconds),
            "pipeline_name": pipeline_name,
            "pipeline_version": pipeline_version,
            "latest_frame_metrics": latest_metrics,
        }

        async with AsyncSessionFactory() as session:
            repository = ProcessingJobRepository(session)

            await repository.update_progress(
                job_id=job_id,
                worker_id=self.worker_id,
                progress_percent=progress_percent,
                last_processed_frame=processed_frames,
                metrics=metrics,
                lease_seconds=(self.settings.worker_lease_seconds),
            )

    async def _mark_succeeded(
        self,
        *,
        job_id: UUID,
        metrics: dict[str, object],
    ) -> None:
        async with AsyncSessionFactory() as session:
            repository = ProcessingJobRepository(session)

            await repository.mark_succeeded(
                job_id=job_id,
                worker_id=self.worker_id,
                metrics=metrics,
            )

    async def _record_failure(
        self,
        *,
        job_id: UUID,
        error_message: str,
    ) -> None:
        async with AsyncSessionFactory() as session:
            repository = ProcessingJobRepository(session)

            resulting_status = await repository.mark_failed_or_retry(
                job_id=job_id,
                worker_id=self.worker_id,
                error_message=error_message,
                maximum_attempts=(self.settings.worker_max_attempts),
            )

        logger.warning(
            "Job %s transitioned to %s.",
            job_id,
            resulting_status.value,
        )

    async def _wait_for_next_poll(self) -> None:
        try:
            await asyncio.wait_for(
                self.stop_event.wait(),
                timeout=(self.settings.worker_poll_interval_seconds),
            )
        except TimeoutError:
            pass

    @staticmethod
    def _timestamp_seconds(
        *,
        capture: cv2.VideoCapture,
        frame_number: int,
        frames_per_second: float | None,
    ) -> float:
        timestamp_milliseconds = capture.get(cv2.CAP_PROP_POS_MSEC)

        if timestamp_milliseconds > 0:
            return float(timestamp_milliseconds / 1000.0)

        if frames_per_second:
            return float(frame_number / frames_per_second)

        return 0.0

    @staticmethod
    def _positive_float(
        value: float,
    ) -> float | None:
        if value <= 0:
            return None

        return float(value)

    @classmethod
    def _positive_integer(
        cls,
        value: float,
    ) -> int | None:
        positive_value = cls._positive_float(value)

        if positive_value is None:
            return None

        return int(positive_value)
