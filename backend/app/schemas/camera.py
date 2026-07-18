from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.enums import CameraStatus


def validate_camera_stream_url(value: str | None) -> str | None:
    """Validate protocols supported by our video-ingestion pipeline."""

    if value is None:
        return None

    normalized_value = value.strip()

    supported_protocols = (
        "rtsp://",
        "rtsps://",
        "http://",
        "https://",
    )

    if not normalized_value.startswith(supported_protocols):
        raise ValueError(
            "Stream URL must use RTSP, RTSPS, HTTP or HTTPS."
        )

    return normalized_value


class CameraCreate(BaseModel):
    """Information required to register a camera."""

    name: str = Field(
        min_length=2,
        max_length=120,
        examples=["MG Road Junction"],
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None
    stream_url: str | None = None

    status: CameraStatus = CameraStatus.INACTIVE

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )

    configured_fps: float | None = Field(
        default=None,
        gt=0,
        le=240,
    )

    resolution_width: int | None = Field(
        default=None,
        gt=0,
    )

    resolution_height: int | None = Field(
        default=None,
        gt=0,
    )

    configuration: dict[str, Any] = Field(
        default_factory=dict,
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Remove unnecessary whitespace from camera names."""

        normalized_value = " ".join(value.split())

        if not normalized_value:
            raise ValueError("Camera name cannot be blank.")

        return normalized_value

    @field_validator("stream_url")
    @classmethod
    def validate_stream_url(
        cls,
        value: str | None,
    ) -> str | None:
        return validate_camera_stream_url(value)


class CameraUpdate(BaseModel):
    """Fields that may be changed on an existing camera."""

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )

    location: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None
    stream_url: str | None = None
    status: CameraStatus | None = None

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )

    configured_fps: float | None = Field(
        default=None,
        gt=0,
        le=240,
    )

    resolution_width: int | None = Field(
        default=None,
        gt=0,
    )

    resolution_height: int | None = Field(
        default=None,
        gt=0,
    )

    configuration: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized_value = " ".join(value.split())

        if not normalized_value:
            raise ValueError("Camera name cannot be blank.")

        return normalized_value

    @field_validator("stream_url")
    @classmethod
    def validate_stream_url(
        cls,
        value: str | None,
    ) -> str | None:
        return validate_camera_stream_url(value)


class CameraRead(BaseModel):
    """Public representation of a registered camera."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    location: str | None
    description: str | None
    stream_url: str | None
    status: CameraStatus
    latitude: float | None
    longitude: float | None
    configured_fps: float | None
    resolution_width: int | None
    resolution_height: int | None
    configuration: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CameraListResponse(BaseModel):
    """Paginated collection of cameras."""

    items: list[CameraRead]
    total: int
    offset: int
    limit: int