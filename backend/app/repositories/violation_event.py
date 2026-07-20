from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.violation_event import ViolationEvent


class ViolationEventRepository:
    """Persist and retrieve detected traffic violations."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

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
