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
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ProcessingJobStatus

if TYPE_CHECKING:
    from app.models.video import Video
    from app.models.violation_event import ViolationEvent


class ProcessingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A background pipeline execution for one video."""

    __tablename__ = "processing_jobs"

    __table_args__ = (
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="progress_percent_range",
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

    status: Mapped[ProcessingJobStatus] = mapped_column(
        Enum(
            ProcessingJobStatus,
            name="processing_job_status",
            native_enum=False,
            values_callable=lambda members: [
                member.value for member in members
            ],
        ),
        nullable=False,
        default=ProcessingJobStatus.QUEUED,
        index=True,
    )

    progress_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    pipeline_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        default="traffic-violation-pipeline",
    )

    pipeline_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    model_versions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    job_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    video: Mapped[Video] = relationship(
        back_populates="processing_jobs",
    )

    violation_events: Mapped[list[ViolationEvent]] = relationship(
        back_populates="processing_job",
    )