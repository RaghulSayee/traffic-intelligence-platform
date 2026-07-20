from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.enums import (
    ReviewStatus,
    ViolationType,
)


class ViolationEventRead(BaseModel):
    """Public representation of a violation event."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    video_id: UUID
    camera_id: UUID | None
    processing_job_id: UUID | None

    event_key: str
    violation_type: ViolationType
    review_status: ReviewStatus

    occurred_at: datetime
    frame_number: int | None
    track_id: str | None

    license_plate: str | None

    detection_confidence: float | None
    rule_confidence: float | None
    ocr_confidence: float | None

    evidence_image_key: str | None
    evidence_clip_key: str | None

    geometry: dict[str, Any]
    event_metadata: dict[str, Any]

    created_at: datetime
    updated_at: datetime


class ViolationEventListResponse(BaseModel):
    """Paginated collection of violation events."""

    items: list[ViolationEventRead]

    total: int
    offset: int
    limit: int


class ViolationReviewUpdate(BaseModel):
    """Human-review decision for a violation."""

    review_status: ReviewStatus

    reviewer: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
    )

    note: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("review_status")
    @classmethod
    def validate_review_status(
        cls,
        value: ReviewStatus,
    ) -> ReviewStatus:
        allowed_statuses = {
            ReviewStatus.CONFIRMED,
            ReviewStatus.REJECTED,
        }

        if value not in allowed_statuses:
            raise ValueError("Review status must be 'confirmed' or 'rejected'.")

        return value

    @field_validator(
        "reviewer",
        "note",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        return normalized or None
