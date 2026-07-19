from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera import Camera
from app.models.enums import CameraStatus


class CameraRepository:
    """Perform database operations for camera records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, camera: Camera) -> Camera:
        """Stage a new camera in the current transaction."""

        self.session.add(camera)
        await self.session.flush()

        return camera

    async def get_by_id(
        self,
        camera_id: UUID,
    ) -> Camera | None:
        """Retrieve a camera using its primary key."""

        return await self.session.get(Camera, camera_id)

    async def get_by_name(
        self,
        name: str,
    ) -> Camera | None:
        """Retrieve a camera using its unique name."""

        statement = select(Camera).where(Camera.name == name)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int,
        limit: int,
        camera_status: CameraStatus | None,
    ) -> list[Camera]:
        """Retrieve cameras using pagination and optional filtering."""

        statement = select(Camera)

        if camera_status is not None:
            statement = statement.where(Camera.status == camera_status)

        statement = (
            statement.order_by(
                Camera.created_at.desc(),
                Camera.id,
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def count(
        self,
        *,
        camera_status: CameraStatus | None,
    ) -> int:
        """Count cameras matching an optional status filter."""

        statement = select(func.count()).select_from(Camera)

        if camera_status is not None:
            statement = statement.where(Camera.status == camera_status)

        result = await self.session.execute(statement)

        return result.scalar_one()

    async def delete(self, camera: Camera) -> None:
        """Stage an existing camera for deletion."""

        await self.session.delete(camera)
        await self.session.flush()
