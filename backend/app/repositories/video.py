from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def get_by_checksum(
        self,
        checksum_sha256: str,
    ) -> Video | None:
        statement = select(Video).where(Video.checksum_sha256 == checksum_sha256)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()
