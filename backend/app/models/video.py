from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import BigInteger, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import VideoSourceType, VideoStatus

if TYPE_CHECKING:
    from app.models.camera import Camera
    from app.models.processing_job import ProcessingJob
    from app.models.violation_event import ViolationEvent


class Video(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A video uploaded or captured for traffic analysis."""

    __tablename__ = "videos"

    camera_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "cameras.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )

    content_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    source_type: Mapped[VideoSourceType] = mapped_column(
        Enum(
            VideoSourceType,
            name="video_source_type",
            native_enum=False,
            values_callable=lambda members: [
                member.value for member in members
            ],
        ),
        nullable=False,
        default=VideoSourceType.UPLOAD,
    )

    status: Mapped[VideoStatus] = mapped_column(
        Enum(
            VideoStatus,
            name="video_status",
            native_enum=False,
            values_callable=lambda members: [
                member.value for member in members
            ],
        ),
        nullable=False,
        default=VideoStatus.UPLOADED,
        index=True,
    )

    size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    frames_per_second: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    frame_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    checksum_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    video_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    camera: Mapped[Camera | None] = relationship(
        back_populates="videos",
    )

    processing_jobs: Mapped[list[ProcessingJob]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )

    violation_events: Mapped[list[ViolationEvent]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )