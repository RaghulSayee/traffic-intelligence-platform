from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import VideoStatus
from app.models.video import Video


class VideoRepository:
    """Perform persistence operations for video records."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create(
        self,
        video: Video,
    ) -> Video:
        self.session.add(video)
        await self.session.flush()

        return video

    async def get_by_id(
        self,
        video_id: UUID,
    ) -> Video | None:
        return await self.session.get(
            Video,
            video_id,
        )

    async def get_by_id_for_delete(
        self,
        video_id: UUID,
    ) -> Video | None:
        """Load a video and its dependent records for deletion."""

        statement = (
            select(Video)
            .where(Video.id == video_id)
            .options(
                selectinload(Video.processing_jobs),
                selectinload(Video.violation_events),
            )
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_checksum(
        self,
        checksum_sha256: str,
    ) -> Video | None:
        statement = select(Video).where(Video.checksum_sha256 == checksum_sha256)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def list_videos(
        self,
        *,
        offset: int,
        limit: int,
        status: VideoStatus | None,
        camera_id: UUID | None,
    ) -> tuple[list[Video], int]:
        """Return videos using pagination and filters."""

        filters = []

        if status is not None:
            filters.append(Video.status == status)

        if camera_id is not None:
            filters.append(Video.camera_id == camera_id)

        count_statement = select(func.count()).select_from(Video)

        list_statement = (
            select(Video).order_by(Video.created_at.desc()).offset(offset).limit(limit)
        )

        if filters:
            count_statement = count_statement.where(*filters)

            list_statement = list_statement.where(*filters)

        count_result = await self.session.execute(count_statement)

        list_result = await self.session.execute(list_statement)

        total = int(count_result.scalar_one())

        videos = list(list_result.scalars().all())

        return videos, total

    async def delete(
        self,
        video: Video,
    ) -> None:
        """Stage a video and its dependent records for deletion."""

        await self.session.delete(video)
        await self.session.flush()
