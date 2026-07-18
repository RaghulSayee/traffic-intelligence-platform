from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CameraNameConflictError,
    CameraNotFoundError,
)
from app.models.camera import Camera
from app.models.enums import CameraStatus
from app.repositories.camera import CameraRepository
from app.schemas.camera import CameraCreate, CameraUpdate


class CameraService:
    """Implement business operations involving cameras."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = CameraRepository(session)

    async def create_camera(
        self,
        payload: CameraCreate,
    ) -> Camera:
        """Register a new traffic camera."""

        existing_camera = await self.repository.get_by_name(
            payload.name
        )

        if existing_camera is not None:
            raise CameraNameConflictError(payload.name)

        camera = Camera(
            **payload.model_dump()
        )

        try:
            await self.repository.create(camera)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()

            raise CameraNameConflictError(
                payload.name
            ) from exc

        await self.session.refresh(camera)

        return camera

    async def get_camera(
        self,
        camera_id: UUID,
    ) -> Camera:
        """Retrieve one camera or raise a domain exception."""

        camera = await self.repository.get_by_id(camera_id)

        if camera is None:
            raise CameraNotFoundError(camera_id)

        return camera

    async def list_cameras(
        self,
        *,
        offset: int,
        limit: int,
        camera_status: CameraStatus | None,
    ) -> tuple[list[Camera], int]:
        """Retrieve a paginated camera collection."""

        cameras = await self.repository.list(
            offset=offset,
            limit=limit,
            camera_status=camera_status,
        )

        total = await self.repository.count(
            camera_status=camera_status,
        )

        return cameras, total

    async def update_camera(
        self,
        camera_id: UUID,
        payload: CameraUpdate,
    ) -> Camera:
        """Apply a partial update to a camera."""

        camera = await self.get_camera(camera_id)

        update_data = payload.model_dump(
            exclude_unset=True
        )

        if not update_data:
            return camera

        requested_name = update_data.get("name")

        if (
            requested_name is not None
            and requested_name != camera.name
        ):
            existing_camera = (
                await self.repository.get_by_name(
                    requested_name
                )
            )

            if (
                existing_camera is not None
                and existing_camera.id != camera.id
            ):
                raise CameraNameConflictError(
                    requested_name
                )

        non_nullable_fields = {
            "name",
            "status",
            "configuration",
        }

        for field_name in non_nullable_fields:
            if (
                field_name in update_data
                and update_data[field_name] is None
            ):
                raise ValueError(
                    f"'{field_name}' cannot be null."
                )

        for field_name, value in update_data.items():
            setattr(camera, field_name, value)

        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()

            conflicting_name = (
                requested_name
                if requested_name is not None
                else camera.name
            )

            raise CameraNameConflictError(
                conflicting_name
            ) from exc

        await self.session.refresh(camera)

        return camera

    async def delete_camera(
        self,
        camera_id: UUID,
    ) -> None:
        """Delete a registered camera."""

        camera = await self.get_camera(camera_id)

        await self.repository.delete(camera)
        await self.session.commit()