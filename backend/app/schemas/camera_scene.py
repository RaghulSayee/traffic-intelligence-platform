from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.models.enums import ViolationType


class NormalizedPoint(BaseModel):
    """A point represented relative to image width and height."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    x: float = Field(
        ge=0.0,
        le=1.0,
    )

    y: float = Field(
        ge=0.0,
        le=1.0,
    )


class NormalizedPolygon(BaseModel):
    """A polygon whose points use normalized image coordinates."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    points: list[NormalizedPoint] = Field(
        min_length=3,
        max_length=100,
    )

    @model_validator(mode="after")
    def validate_distinct_points(
        self,
    ) -> "NormalizedPolygon":
        distinct_points = {
            (
                point.x,
                point.y,
            )
            for point in self.points
        }

        if len(distinct_points) < 3:
            raise ValueError("A polygon requires at least three distinct points.")

        return self


class NormalizedLine(BaseModel):
    """A line segment using normalized coordinates."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    start: NormalizedPoint
    end: NormalizedPoint

    @model_validator(mode="after")
    def validate_different_endpoints(
        self,
    ) -> "NormalizedLine":
        if self.start == self.end:
            raise ValueError("A line must have different start and end points.")

        return self


class NormalizedDirection(BaseModel):
    """Expected direction of travel in image coordinates."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    x: float = Field(
        ge=-1.0,
        le=1.0,
    )

    y: float = Field(
        ge=-1.0,
        le=1.0,
    )

    @model_validator(mode="after")
    def validate_nonzero_direction(
        self,
    ) -> "NormalizedDirection":
        if self.x == 0.0 and self.y == 0.0:
            raise ValueError("A direction vector cannot be zero.")

        return self


class LaneConfiguration(BaseModel):
    """One configured traffic lane."""

    model_config = ConfigDict(
        extra="forbid",
    )

    lane_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    name: str | None = Field(
        default=None,
        max_length=120,
    )

    polygon: NormalizedPolygon

    allowed_direction: NormalizedDirection

    speed_limit_kph: float | None = Field(
        default=None,
        gt=0,
        le=300,
    )


class TrafficLightRegionConfiguration(BaseModel):
    """Image region containing one traffic signal."""

    model_config = ConfigDict(
        extra="forbid",
    )

    region_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    name: str | None = Field(
        default=None,
        max_length=120,
    )

    polygon: NormalizedPolygon


class StopLineConfiguration(BaseModel):
    """A stop line associated with a lane and traffic signal."""

    model_config = ConfigDict(
        extra="forbid",
    )

    stop_line_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    lane_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )

    traffic_light_region_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )

    line: NormalizedLine


class SpeedCalibrationSegment(BaseModel):
    """A known real-world distance visible in the camera frame."""

    model_config = ConfigDict(
        extra="forbid",
    )

    segment_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    line: NormalizedLine

    distance_meters: float = Field(
        gt=0,
        le=5000,
    )


class CameraSceneConfiguration(BaseModel):
    """Validated road-scene configuration for one camera."""

    model_config = ConfigDict(
        extra="forbid",
    )

    schema_version: Literal["1.0"] = "1.0"

    enabled_violations: list[ViolationType] = Field(
        default_factory=list,
    )

    monitoring_zone: NormalizedPolygon | None = None

    lanes: list[LaneConfiguration] = Field(
        default_factory=list,
        max_length=100,
    )

    traffic_light_regions: list[TrafficLightRegionConfiguration] = Field(
        default_factory=list,
        max_length=50,
    )

    stop_lines: list[StopLineConfiguration] = Field(
        default_factory=list,
        max_length=100,
    )

    speed_calibration_segments: list[SpeedCalibrationSegment] = Field(
        default_factory=list,
        max_length=50,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(mode="after")
    def validate_scene_references(
        self,
    ) -> "CameraSceneConfiguration":
        self._ensure_unique(
            [lane.lane_id for lane in self.lanes],
            entity_name="lane",
        )

        self._ensure_unique(
            [region.region_id for region in self.traffic_light_regions],
            entity_name="traffic-light region",
        )

        self._ensure_unique(
            [stop_line.stop_line_id for stop_line in self.stop_lines],
            entity_name="stop line",
        )

        self._ensure_unique(
            [segment.segment_id for segment in self.speed_calibration_segments],
            entity_name="calibration segment",
        )

        lane_ids = {lane.lane_id for lane in self.lanes}

        traffic_light_ids = {region.region_id for region in self.traffic_light_regions}

        for stop_line in self.stop_lines:
            if stop_line.lane_id is not None and stop_line.lane_id not in lane_ids:
                raise ValueError(
                    "Stop line "
                    f"'{stop_line.stop_line_id}' references "
                    f"unknown lane '{stop_line.lane_id}'."
                )

            if (
                stop_line.traffic_light_region_id is not None
                and stop_line.traffic_light_region_id not in traffic_light_ids
            ):
                raise ValueError(
                    "Stop line "
                    f"'{stop_line.stop_line_id}' references "
                    "unknown traffic-light region "
                    f"'{stop_line.traffic_light_region_id}'."
                )

        if len(set(self.enabled_violations)) != len(self.enabled_violations):
            raise ValueError("Enabled violation types must be unique.")

        return self

    @staticmethod
    def _ensure_unique(
        values: list[str],
        *,
        entity_name: str,
    ) -> None:
        if len(values) != len(set(values)):
            raise ValueError(f"Each {entity_name} ID must be unique.")
