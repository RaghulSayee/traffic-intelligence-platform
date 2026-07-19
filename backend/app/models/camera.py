from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import CameraStatus

if TYPE_CHECKING:
    from app.models.video import Video
    from app.models.violation_event import ViolationEvent


class Camera(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A physical or network camera monitoring a road scene."""

    __tablename__ = "cameras"

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
        index=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    stream_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[CameraStatus] = mapped_column(
        Enum(
            CameraStatus,
            name="camera_status",
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        nullable=False,
        default=CameraStatus.INACTIVE,
        index=True,
    )

    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    configured_fps: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    resolution_width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    resolution_height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    videos: Mapped[list[Video]] = relationship(
        back_populates="camera",
        passive_deletes=True,
    )

    violation_events: Mapped[list[ViolationEvent]] = relationship(
        back_populates="camera",
        passive_deletes=True,
    )
