import asyncio
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CameraNotFoundError,
    DuplicateVideoError,
    UnsupportedVideoError,
)
from app.media.metadata import VideoMetadataExtractor
from app.models.enums import (
    ProcessingJobStatus,
    VideoSourceType,
    VideoStatus,
)
from app.models.processing_job import ProcessingJob
from app.models.video import Video
from app.repositories.camera import CameraRepository
from app.repositories.processing_job import (
    ProcessingJobRepository,
)
from app.repositories.video import VideoRepository
from app.storage.base import StoredVideo, VideoStorage


ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/avi",
    "video/x-matroska",
    "video/webm",
    "application/octet-stream",
}


class VideoIngestionService:
    """Coordinate video storage, validation and persistence."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        storage: VideoStorage,
        metadata_extractor: VideoMetadataExtractor,
    ) -> None:
        self.session = session
        self.storage = storage
        self.metadata_extractor = metadata_extractor

        self.camera_repository = CameraRepository(session)
        self.video_repository = VideoRepository(session)
        self.job_repository = ProcessingJobRepository(session)

    async def ingest(
        self,
        *,
        upload: UploadFile,
        camera_id: UUID | None,
        priority: int,
    ) -> tuple[Video, ProcessingJob]:
        """Store and register one uploaded video."""

        filename = Path(upload.filename or "").name

        if not filename:
            raise UnsupportedVideoError("The uploaded video must have a filename.")

        if (
            upload.content_type is not None
            and upload.content_type not in ALLOWED_CONTENT_TYPES
        ):
            raise UnsupportedVideoError(
                f"Unsupported content type: {upload.content_type}."
            )

        if camera_id is not None:
            camera = await self.camera_repository.get_by_id(camera_id)

            if camera is None:
                raise CameraNotFoundError(camera_id)

        stored_video: StoredVideo | None = None

        try:
            stored_video = await self.storage.save(upload)

            existing_video = await self.video_repository.get_by_checksum(
                stored_video.checksum_sha256
            )

            if existing_video is not None:
                raise DuplicateVideoError(stored_video.checksum_sha256)

            metadata = await asyncio.to_thread(
                self.metadata_extractor.extract,
                stored_video.path,
            )

            video = Video(
                camera_id=camera_id,
                original_filename=filename,
                storage_key=stored_video.key,
                content_type=upload.content_type,
                source_type=VideoSourceType.UPLOAD,
                status=VideoStatus.QUEUED,
                size_bytes=stored_video.size_bytes,
                duration_seconds=metadata.duration_seconds,
                frames_per_second=metadata.frames_per_second,
                frame_count=metadata.frame_count,
                width=metadata.width,
                height=metadata.height,
                checksum_sha256=stored_video.checksum_sha256,
                video_metadata={
                    "codec": metadata.codec,
                },
            )

            await self.video_repository.create(video)

            processing_job = ProcessingJob(
                video_id=video.id,
                status=ProcessingJobStatus.QUEUED,
                priority=priority,
                pipeline_name=("traffic-violation-pipeline"),
                pipeline_version=None,
                model_versions={},
                job_metrics={},
            )

            await self.job_repository.create(processing_job)

            await self.session.commit()

            await self.session.refresh(video)
            await self.session.refresh(processing_job)

            return video, processing_job

        except DuplicateVideoError:
            await self.session.rollback()

            if stored_video is not None:
                await self.storage.delete(stored_video.key)

            raise

        except IntegrityError as exc:
            await self.session.rollback()

            if stored_video is not None:
                await self.storage.delete(stored_video.key)

            checksum = (
                stored_video.checksum_sha256 if stored_video is not None else "unknown"
            )

            raise DuplicateVideoError(checksum) from exc

        except Exception:
            await self.session.rollback()

            if stored_video is not None:
                await self.storage.delete(stored_video.key)

            raise
