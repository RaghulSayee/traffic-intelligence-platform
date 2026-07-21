from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from app.models.enums import ViolationType
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
    LaneConfiguration,
    NormalizedPoint,
)
from app.scene.geometry import (
    normalized_point_in_polygon,
    normalized_polygon_to_pixels,
    point_to_polygon_edge_distance,
)
from app.tracking.types import TrackedObject


VEHICLE_CLASS_NAMES = frozenset(
    {
        "bicycle",
        "car",
        "motorcycle",
        "bus",
        "truck",
    }
)


@dataclass(frozen=True, slots=True)
class LaneOccupancyObservation:
    """Lane occupancy information for one visible vehicle."""

    track_id: int
    class_name: str

    lane_id: str | None
    nearest_lane_id: str | None

    anchor_x_normalized: float
    anchor_y_normalized: float

    distance_to_nearest_lane_pixels: float | None

    velocity_x: float
    velocity_y: float
    speed_pixels_per_second: float

    inside_monitoring_zone: bool
    outside_configured_lanes: bool
    within_boundary_tolerance: bool
    violation_candidate: bool


@dataclass(frozen=True, slots=True)
class LaneOccupancyResult:
    """Lane occupancy observations for one frame."""

    observations: tuple[
        LaneOccupancyObservation,
        ...,
    ]

    @property
    def violation_candidates(
        self,
    ) -> tuple[
        LaneOccupancyObservation,
        ...,
    ]:
        """Return vehicles eligible for temporal confirmation."""

        return tuple(
            observation
            for observation in self.observations
            if observation.violation_candidate
        )


class LaneOccupancyAnalyzer:
    """
    Determine whether visible vehicles occupy configured lanes.

    A lane-violation candidate must:
    1. Be a confirmed visible vehicle.
    2. Be inside the monitoring zone.
    3. Be outside all configured lane polygons.
    4. Be farther than the boundary tolerance.
    5. Be moving faster than the minimum speed.
    """

    def __init__(
        self,
        *,
        minimum_speed_pixels_per_second: float,
        boundary_tolerance_pixels: float,
    ) -> None:
        if minimum_speed_pixels_per_second < 0:
            raise ValueError("Minimum speed cannot be negative.")

        if boundary_tolerance_pixels < 0:
            raise ValueError("Boundary tolerance cannot be negative.")

        self.minimum_speed_pixels_per_second = minimum_speed_pixels_per_second

        self.boundary_tolerance_pixels = boundary_tolerance_pixels

    def analyze(
        self,
        *,
        tracks: tuple[TrackedObject, ...],
        scene: CameraSceneConfiguration | None,
        image_width: int,
        image_height: int,
    ) -> LaneOccupancyResult:
        """Analyze lane occupancy for one frame."""

        if image_width <= 0 or image_height <= 0:
            raise ValueError("Image dimensions must be positive.")

        if (
            scene is None
            or ViolationType.LANE_VIOLATION not in scene.enabled_violations
            or not scene.lanes
        ):
            return LaneOccupancyResult(
                observations=(),
            )

        observations = []

        for track in tracks:
            if not self._eligible_track(track):
                continue

            observation = self._analyze_track(
                track=track,
                scene=scene,
                image_width=image_width,
                image_height=image_height,
            )

            observations.append(observation)

        return LaneOccupancyResult(
            observations=tuple(observations),
        )

    def _analyze_track(
        self,
        *,
        track: TrackedObject,
        scene: CameraSceneConfiguration,
        image_width: int,
        image_height: int,
    ) -> LaneOccupancyObservation:
        anchor = self._road_anchor(
            track=track,
            image_width=image_width,
            image_height=image_height,
        )

        inside_monitoring_zone = (
            scene.monitoring_zone is None
            or normalized_point_in_polygon(
                point=anchor,
                polygon=scene.monitoring_zone,
            )
        )

        containing_lane = self._find_containing_lane(
            anchor=anchor,
            lanes=scene.lanes,
        )

        nearest_lane_id: str | None
        distance_to_nearest_lane: float | None

        if containing_lane is not None:
            nearest_lane_id = containing_lane.lane_id

            distance_to_nearest_lane = 0.0

        else:
            (
                nearest_lane_id,
                distance_to_nearest_lane,
            ) = self._nearest_lane(
                anchor=anchor,
                lanes=scene.lanes,
                image_width=image_width,
                image_height=image_height,
            )

        speed = hypot(
            track.velocity_x,
            track.velocity_y,
        )

        outside_configured_lanes = containing_lane is None

        within_boundary_tolerance = (
            outside_configured_lanes
            and distance_to_nearest_lane is not None
            and distance_to_nearest_lane <= self.boundary_tolerance_pixels
        )

        violation_candidate = (
            inside_monitoring_zone
            and outside_configured_lanes
            and not within_boundary_tolerance
            and speed >= self.minimum_speed_pixels_per_second
        )

        return LaneOccupancyObservation(
            track_id=track.track_id,
            class_name=track.class_name,
            lane_id=(containing_lane.lane_id if containing_lane is not None else None),
            nearest_lane_id=nearest_lane_id,
            anchor_x_normalized=anchor.x,
            anchor_y_normalized=anchor.y,
            distance_to_nearest_lane_pixels=(distance_to_nearest_lane),
            velocity_x=track.velocity_x,
            velocity_y=track.velocity_y,
            speed_pixels_per_second=speed,
            inside_monitoring_zone=(inside_monitoring_zone),
            outside_configured_lanes=(outside_configured_lanes),
            within_boundary_tolerance=(within_boundary_tolerance),
            violation_candidate=(violation_candidate),
        )

    @staticmethod
    def _road_anchor(
        *,
        track: TrackedObject,
        image_width: int,
        image_height: int,
    ) -> NormalizedPoint:
        """Return the lower-center vehicle road anchor."""

        denominator_x = max(
            image_width - 1,
            1,
        )

        denominator_y = max(
            image_height - 1,
            1,
        )

        center_x, _ = track.bounding_box.center

        anchor_y = track.bounding_box.y1 + track.bounding_box.height * 0.90

        return NormalizedPoint(
            x=min(
                max(
                    center_x / denominator_x,
                    0.0,
                ),
                1.0,
            ),
            y=min(
                max(
                    anchor_y / denominator_y,
                    0.0,
                ),
                1.0,
            ),
        )

    @staticmethod
    def _find_containing_lane(
        *,
        anchor: NormalizedPoint,
        lanes: list[LaneConfiguration],
    ) -> LaneConfiguration | None:
        """Return the first lane containing the anchor."""

        for lane in lanes:
            if normalized_point_in_polygon(
                point=anchor,
                polygon=lane.polygon,
            ):
                return lane

        return None

    @staticmethod
    def _nearest_lane(
        *,
        anchor: NormalizedPoint,
        lanes: list[LaneConfiguration],
        image_width: int,
        image_height: int,
    ) -> tuple[str | None, float | None]:
        """Return the closest configured lane and distance."""

        anchor_pixel = (
            anchor.x
            * max(
                image_width - 1,
                1,
            ),
            anchor.y
            * max(
                image_height - 1,
                1,
            ),
        )

        nearest_lane_id: str | None = None
        nearest_distance: float | None = None

        for lane in lanes:
            polygon_pixels = normalized_polygon_to_pixels(
                lane.polygon,
                image_width=image_width,
                image_height=image_height,
            )

            distance = point_to_polygon_edge_distance(
                point=anchor_pixel,
                polygon=polygon_pixels,
            )

            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest_lane_id = lane.lane_id

        return (
            nearest_lane_id,
            nearest_distance,
        )

    @staticmethod
    def _eligible_track(
        track: TrackedObject,
    ) -> bool:
        """Return whether a track can participate."""

        return (
            track.confirmed
            and track.missed_frames == 0
            and track.class_name in VEHICLE_CLASS_NAMES
        )
