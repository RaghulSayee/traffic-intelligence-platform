from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ViolationEventNotFoundError,
)
from app.models.enums import (
    ReviewStatus,
    ViolationType,
)
from app.models.violation_event import ViolationEvent
from app.repositories.violation_event import (
    ViolationEventRepository,
)
from app.schemas.violation_event import (
    ViolationReviewUpdate,
)


class ViolationEventService:
    """Provide violation query and review operations."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.repository = ViolationEventRepository(session)

    async def get_violation(
        self,
        violation_id: UUID,
    ) -> ViolationEvent:
        """Return one violation or raise a domain error."""

        violation = await self.repository.get_by_id(violation_id)

        if violation is None:
            raise ViolationEventNotFoundError(violation_id)

        return violation

    async def list_violations(
        self,
        *,
        offset: int,
        limit: int,
        violation_type: ViolationType | None,
        review_status: ReviewStatus | None,
        video_id: UUID | None,
        processing_job_id: UUID | None,
        camera_id: UUID | None,
    ) -> tuple[list[ViolationEvent], int]:
        """Return a filtered, paginated collection."""

        violations = await self.repository.list(
            offset=offset,
            limit=limit,
            violation_type=violation_type,
            review_status=review_status,
            video_id=video_id,
            processing_job_id=(processing_job_id),
            camera_id=camera_id,
        )

        total = await self.repository.count(
            violation_type=violation_type,
            review_status=review_status,
            video_id=video_id,
            processing_job_id=(processing_job_id),
            camera_id=camera_id,
        )

        return violations, total

    async def review_violation(
        self,
        violation_id: UUID,
        payload: ViolationReviewUpdate,
    ) -> ViolationEvent:
        """Confirm or reject a detected violation."""

        violation = await self.get_violation(violation_id)

        reviewed_at = datetime.now(timezone.utc)

        metadata = dict(violation.event_metadata or {})

        metadata["review"] = {
            "status": payload.review_status.value,
            "reviewed_at": (reviewed_at.isoformat()),
            "reviewer": payload.reviewer,
            "note": payload.note,
        }

        violation.review_status = payload.review_status

        violation.event_metadata = metadata

        await self.repository.commit()
        await self.repository.refresh(violation)

        return violation
