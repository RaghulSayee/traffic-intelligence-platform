from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ReviewStatus, ViolationType

if TYPE_CHECKING:
    from app.models.camera import Camera
    from app.models.processing_job import ProcessingJob
    from app.models.video import Video


class ViolationEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A traffic-rule violation detected across one or more frames."""

    __tablename__ = "violation_events"

    __table_args__ = (
        CheckConstraint(
            (
                "detection_confidence IS NULL OR "
                "(detection_confidence >= 0 "
                "AND detection_confidence <= 1)"
            ),
            name="detection_confidence_range",
        ),
        CheckConstraint(
            (
                "rule_confidence IS NULL OR "
                "(rule_confidence >= 0 AND rule_confidence <= 1)"
            ),
            name="rule_confidence_range",
        ),
        CheckConstraint(
            ("ocr_confidence IS NULL OR (ocr_confidence >= 0 AND ocr_confidence <= 1)"),
            name="ocr_confidence_range",
        ),
        Index(
            "ix_violation_event_time_type",
            "occurred_at",
            "violation_type",
        ),
    )

    video_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "videos.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    camera_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "cameras.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    processing_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "processing_jobs.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    event_key: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
        unique=True,
    )

    violation_type: Mapped[ViolationType] = mapped_column(
        Enum(
            ViolationType,
            name="violation_type",
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        nullable=False,
        index=True,
    )

    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(
            ReviewStatus,
            name="review_status",
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        nullable=False,
        default=ReviewStatus.PENDING,
        index=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    frame_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    track_id: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        index=True,
    )

    license_plate: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )

    detection_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    rule_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    ocr_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    evidence_image_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    evidence_clip_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    geometry: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    video: Mapped[Video] = relationship(
        back_populates="violation_events",
    )

    camera: Mapped[Camera | None] = relationship(
        back_populates="violation_events",
    )

    processing_job: Mapped[ProcessingJob | None] = relationship(
        back_populates="violation_events",
    )
