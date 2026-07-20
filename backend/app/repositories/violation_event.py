from __future__ import annotations
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    ReviewStatus,
    ViolationType,
)
from app.models.violation_event import ViolationEvent


class ViolationEventRepository:
    """Persist and query detected traffic violations."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_by_id(
        self,
        violation_id: UUID,
    ) -> ViolationEvent | None:
        """Return a violation using its primary key."""

        return await self.session.get(
            ViolationEvent,
            violation_id,
        )

    async def get_by_event_key(
        self,
        event_key: str,
        *,
        for_update: bool = False,
    ) -> ViolationEvent | None:
        """Return one event using its deterministic key."""

        statement = select(ViolationEvent).where(ViolationEvent.event_key == event_key)

        if for_update:
            statement = statement.with_for_update()

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def create(
        self,
        event: ViolationEvent,
    ) -> ViolationEvent:
        """Insert a new violation event."""

        self.session.add(event)
        await self.session.flush()

        return event

    async def list(
        self,
        *,
        offset: int,
        limit: int,
        violation_type: ViolationType | None,
        review_status: ReviewStatus | None,
        video_id: UUID | None,
        processing_job_id: UUID | None,
        camera_id: UUID | None,
    ) -> list[ViolationEvent]:
        """Return violations using filters and pagination."""

        statement = select(ViolationEvent)

        conditions = self._build_conditions(
            violation_type=violation_type,
            review_status=review_status,
            video_id=video_id,
            processing_job_id=processing_job_id,
            camera_id=camera_id,
        )

        if conditions:
            statement = statement.where(*conditions)

        statement = (
            statement.order_by(
                ViolationEvent.occurred_at.desc(),
                ViolationEvent.created_at.desc(),
                ViolationEvent.id,
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def count(
        self,
        *,
        violation_type: ViolationType | None,
        review_status: ReviewStatus | None,
        video_id: UUID | None,
        processing_job_id: UUID | None,
        camera_id: UUID | None,
    ) -> int:
        """Count violations matching the supplied filters."""

        statement = select(func.count()).select_from(ViolationEvent)

        conditions = self._build_conditions(
            violation_type=violation_type,
            review_status=review_status,
            video_id=video_id,
            processing_job_id=processing_job_id,
            camera_id=camera_id,
        )

        if conditions:
            statement = statement.where(*conditions)

        result = await self.session.execute(statement)

        return result.scalar_one()

    async def list_by_processing_job(
        self,
        processing_job_id: UUID,
        *,
        for_update: bool = False,
    ) -> list[ViolationEvent]:
        """Return violations produced by one processing job."""

        statement = (
            select(ViolationEvent)
            .where(ViolationEvent.processing_job_id == processing_job_id)
            .order_by(
                ViolationEvent.occurred_at,
                ViolationEvent.created_at,
            )
        )

        if for_update:
            statement = statement.with_for_update()

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def commit(self) -> None:
        """Commit repository changes."""

        await self.session.commit()

    async def refresh(
        self,
        event: ViolationEvent,
    ) -> None:
        """Refresh an event after committing changes."""

        await self.session.refresh(event)

    @staticmethod
    def _build_conditions(
        *,
        violation_type: ViolationType | None,
        review_status: ReviewStatus | None,
        video_id: UUID | None,
        processing_job_id: UUID | None,
        camera_id: UUID | None,
    ) -> list:
        """Build reusable SQLAlchemy filter expressions."""

        conditions = []

        if violation_type is not None:
            conditions.append(ViolationEvent.violation_type == violation_type)

        if review_status is not None:
            conditions.append(ViolationEvent.review_status == review_status)

        if video_id is not None:
            conditions.append(ViolationEvent.video_id == video_id)

        if processing_job_id is not None:
            conditions.append(ViolationEvent.processing_job_id == processing_job_id)

        if camera_id is not None:
            conditions.append(ViolationEvent.camera_id == camera_id)

        return conditions
