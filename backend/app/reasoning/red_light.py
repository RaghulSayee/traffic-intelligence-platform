from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import hypot

from app.models.enums import ViolationType
from app.reasoning.traffic_light_state import (
    TrafficLightState,
)
from app.reasoning.traffic_light_temporal import (
    StableTrafficLightSnapshot,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
    LaneConfiguration,
    NormalizedPoint,
    StopLineConfiguration,
)
from app.scene.geometry import (
    normalized_line_to_pixels,
    normalized_point_in_polygon,
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


RedLightStateKey = tuple[int, str]

PixelPointFloat = tuple[float, float]


class RedLightTransitionType(StrEnum):
    """Lifecycle transition emitted when a vehicle crosses on red."""

    STARTED = "started"


@dataclass(frozen=True, slots=True)
class RedLightCrossingObservation:
    """One vehicle crossing a configured stop line."""

    track_id: int
    class_name: str

    stop_line_id: str
    lane_id: str
    traffic_light_region_id: str

    signal_state: TrafficLightState
    signal_confidence: float

    previous_frame_number: int
    frame_number: int
    timestamp_seconds: float

    previous_anchor_x_normalized: float
    previous_anchor_y_normalized: float

    anchor_x_normalized: float
    anchor_y_normalized: float

    previous_signed_distance_pixels: float
    signed_distance_pixels: float
    crossing_depth_pixels: float

    velocity_x: float
    velocity_y: float
    speed_pixels_per_second: float
    direction_cosine: float

    detection_confidence: float
    rule_confidence: float

    is_violation: bool


@dataclass(frozen=True, slots=True)
class RedLightViolationTransition:
    """A confirmed red-light stop-line crossing."""

    transition_type: RedLightTransitionType

    track_id: int
    class_name: str

    stop_line_id: str
    lane_id: str
    traffic_light_region_id: str

    signal_state: TrafficLightState
    signal_confidence: float

    previous_frame_number: int
    frame_number: int
    timestamp_seconds: float

    previous_anchor_x_normalized: float
    previous_anchor_y_normalized: float

    anchor_x_normalized: float
    anchor_y_normalized: float

    previous_signed_distance_pixels: float
    signed_distance_pixels: float
    crossing_depth_pixels: float

    velocity_x: float
    velocity_y: float
    speed_pixels_per_second: float
    direction_cosine: float

    detection_confidence: float
    rule_confidence: float


@dataclass(frozen=True, slots=True)
class RedLightDetectionResult:
    """Stop-line crossings and red-light violations for one frame."""

    observations: tuple[
        RedLightCrossingObservation,
        ...,
    ]

    transitions: tuple[
        RedLightViolationTransition,
        ...,
    ] = ()

    @property
    def violation_count(
        self,
    ) -> int:
        """Return the number of violations emitted this frame."""

        return len(self.transitions)


@dataclass(slots=True)
class _TrackStopLineState:
    """Previous road-anchor state for one track and stop line."""

    track_id: int
    stop_line_id: str

    previous_frame_number: int

    previous_anchor_pixel: PixelPointFloat
    previous_anchor_normalized: NormalizedPoint

    previous_signed_distance_pixels: float
    previous_inside_lane: bool

    violation_emitted: bool

    missed_frames: int
    observed_this_frame: bool


class RedLightCrossingDetector:
    """
    Detect vehicles crossing a configured stop line during red.

    A violation requires:

    1. A visible confirmed vehicle track.
    2. A stop line linked to a lane and traffic-light region.
    3. Movement across the finite stop-line segment.
    4. Movement in the lane's configured legal direction.
    5. Minimum vehicle speed and directional alignment.
    6. A stable red signal with sufficient confidence.
    """

    def __init__(
        self,
        *,
        minimum_speed_pixels_per_second: float,
        minimum_direction_cosine: float,
        line_crossing_tolerance_pixels: float,
        minimum_signal_confidence: float,
        maximum_missed_frames: int,
    ) -> None:
        if minimum_speed_pixels_per_second < 0:
            raise ValueError("Minimum speed cannot be negative.")

        if not 0.0 <= minimum_direction_cosine <= 1.0:
            raise ValueError("Minimum direction cosine must be between zero and one.")

        if line_crossing_tolerance_pixels <= 0:
            raise ValueError("Line crossing tolerance must be positive.")

        if not 0.0 <= minimum_signal_confidence <= 1.0:
            raise ValueError("Minimum signal confidence must be between zero and one.")

        if maximum_missed_frames < 0:
            raise ValueError("Maximum missed frames cannot be negative.")

        self.minimum_speed_pixels_per_second = minimum_speed_pixels_per_second

        self.minimum_direction_cosine = minimum_direction_cosine

        self.line_crossing_tolerance_pixels = line_crossing_tolerance_pixels

        self.minimum_signal_confidence = minimum_signal_confidence

        self.maximum_missed_frames = maximum_missed_frames

        self._states: dict[
            RedLightStateKey,
            _TrackStopLineState,
        ] = {}

    def update(
        self,
        *,
        frame_number: int,
        timestamp_seconds: float,
        tracks: tuple[TrackedObject, ...],
        traffic_light_states: tuple[
            StableTrafficLightSnapshot,
            ...,
        ],
        scene: CameraSceneConfiguration | None,
        image_width: int,
        image_height: int,
    ) -> RedLightDetectionResult:
        """Evaluate stop-line crossings for one analyzed frame."""

        if frame_number <= 0:
            raise ValueError("Frame number must be positive.")

        if timestamp_seconds < 0:
            raise ValueError("Timestamp cannot be negative.")

        if image_width <= 0 or image_height <= 0:
            raise ValueError("Image dimensions must be positive.")

        for state in self._states.values():
            state.observed_this_frame = False

        if (
            scene is None
            or ViolationType.RED_LIGHT not in scene.enabled_violations
            or not scene.stop_lines
        ):
            self.reset()

            return RedLightDetectionResult(
                observations=(),
                transitions=(),
            )

        lanes_by_id = {lane.lane_id: lane for lane in scene.lanes}

        signal_states_by_region = {
            state.region_id: state for state in traffic_light_states
        }

        observations: list[RedLightCrossingObservation] = []

        transitions: list[RedLightViolationTransition] = []

        for track in tracks:
            if not self._eligible_track(track):
                continue

            anchor_pixel = self._road_anchor_pixel(track)

            anchor_normalized = self._road_anchor_normalized(
                anchor_pixel=anchor_pixel,
                image_width=image_width,
                image_height=image_height,
            )

            for stop_line in scene.stop_lines:
                if (
                    stop_line.lane_id is None
                    or stop_line.traffic_light_region_id is None
                ):
                    continue

                lane = lanes_by_id.get(stop_line.lane_id)

                if lane is None:
                    continue

                key = (
                    track.track_id,
                    stop_line.stop_line_id,
                )

                existing_state = self._states.get(key)

                inside_lane = normalized_point_in_polygon(
                    point=anchor_normalized,
                    polygon=lane.polygon,
                )

                if existing_state is None and not inside_lane:
                    continue

                stop_line_pixels = normalized_line_to_pixels(
                    stop_line.line,
                    image_width=image_width,
                    image_height=image_height,
                )

                direction_sign = self._legal_direction_sign(
                    lane=lane,
                    stop_line_pixels=stop_line_pixels,
                    image_width=image_width,
                    image_height=image_height,
                )

                if direction_sign is None:
                    continue

                signed_distance = (
                    self._signed_distance_to_line(
                        point=anchor_pixel,
                        line_start=(stop_line_pixels[0]),
                        line_end=(stop_line_pixels[1]),
                    )
                    * direction_sign
                )

                if existing_state is None:
                    self._states[key] = _TrackStopLineState(
                        track_id=track.track_id,
                        stop_line_id=(stop_line.stop_line_id),
                        previous_frame_number=(frame_number),
                        previous_anchor_pixel=(anchor_pixel),
                        previous_anchor_normalized=(anchor_normalized),
                        previous_signed_distance_pixels=(signed_distance),
                        previous_inside_lane=(inside_lane),
                        violation_emitted=False,
                        missed_frames=0,
                        observed_this_frame=True,
                    )

                    continue

                existing_state.observed_this_frame = True
                existing_state.missed_frames = 0

                crossing = self._evaluate_crossing(
                    track=track,
                    lane=lane,
                    stop_line=stop_line,
                    stop_line_pixels=stop_line_pixels,
                    state=existing_state,
                    anchor_pixel=anchor_pixel,
                    anchor_normalized=(anchor_normalized),
                    signed_distance_pixels=(signed_distance),
                    signal_state=(
                        signal_states_by_region.get(stop_line.traffic_light_region_id)
                    ),
                    frame_number=frame_number,
                    timestamp_seconds=(timestamp_seconds),
                    image_width=image_width,
                    image_height=image_height,
                )

                if crossing is not None:
                    observations.append(crossing)

                    if crossing.is_violation:
                        transition = self._create_transition(crossing)

                        transitions.append(transition)

                        existing_state.violation_emitted = True

                existing_state.previous_frame_number = frame_number

                existing_state.previous_anchor_pixel = anchor_pixel

                existing_state.previous_anchor_normalized = anchor_normalized

                existing_state.previous_signed_distance_pixels = signed_distance

                existing_state.previous_inside_lane = inside_lane

        self._expire_missing_states()

        return RedLightDetectionResult(
            observations=tuple(observations),
            transitions=tuple(transitions),
        )

    def reset(self) -> None:
        """Clear all track and stop-line history."""

        self._states.clear()

    def _evaluate_crossing(
        self,
        *,
        track: TrackedObject,
        lane: LaneConfiguration,
        stop_line: StopLineConfiguration,
        stop_line_pixels: tuple[
            tuple[int, int],
            tuple[int, int],
        ],
        state: _TrackStopLineState,
        anchor_pixel: PixelPointFloat,
        anchor_normalized: NormalizedPoint,
        signed_distance_pixels: float,
        signal_state: StableTrafficLightSnapshot | None,
        frame_number: int,
        timestamp_seconds: float,
        image_width: int,
        image_height: int,
    ) -> RedLightCrossingObservation | None:
        """Return an observation when the road anchor crosses."""

        if not state.previous_inside_lane:
            return None

        previous_distance = state.previous_signed_distance_pixels

        crossing_depth = signed_distance_pixels - previous_distance

        crossed_legal_side = previous_distance < 0.0 and signed_distance_pixels >= 0.0

        if not crossed_legal_side:
            return None

        if crossing_depth < 2.0 * self.line_crossing_tolerance_pixels:
            return None

        if not self._segments_intersect(
            first_start=(state.previous_anchor_pixel),
            first_end=anchor_pixel,
            second_start=(stop_line_pixels[0]),
            second_end=(stop_line_pixels[1]),
        ):
            return None

        speed = hypot(
            track.velocity_x,
            track.velocity_y,
        )

        if speed < self.minimum_speed_pixels_per_second:
            return None

        direction_cosine = self._direction_cosine(
            track=track,
            lane=lane,
            image_width=image_width,
            image_height=image_height,
        )

        if direction_cosine < self.minimum_direction_cosine:
            return None

        stable_signal_state = (
            signal_state.stable_state
            if signal_state is not None
            else TrafficLightState.UNKNOWN
        )

        signal_confidence = (
            signal_state.stable_confidence if signal_state is not None else 0.0
        )

        crossing_strength = min(
            crossing_depth
            / max(
                2.0 * self.line_crossing_tolerance_pixels,
                1.0,
            ),
            1.0,
        )

        rule_confidence = self._clamp01(
            0.50 * signal_confidence
            + 0.30
            * max(
                direction_cosine,
                0.0,
            )
            + 0.20 * crossing_strength
        )

        is_red = (
            stable_signal_state == TrafficLightState.RED
            and signal_confidence >= self.minimum_signal_confidence
        )

        is_violation = is_red and not state.violation_emitted

        return RedLightCrossingObservation(
            track_id=track.track_id,
            class_name=track.class_name,
            stop_line_id=(stop_line.stop_line_id),
            lane_id=lane.lane_id,
            traffic_light_region_id=(stop_line.traffic_light_region_id),
            signal_state=stable_signal_state,
            signal_confidence=(signal_confidence),
            previous_frame_number=(state.previous_frame_number),
            frame_number=frame_number,
            timestamp_seconds=(timestamp_seconds),
            previous_anchor_x_normalized=(state.previous_anchor_normalized.x),
            previous_anchor_y_normalized=(state.previous_anchor_normalized.y),
            anchor_x_normalized=(anchor_normalized.x),
            anchor_y_normalized=(anchor_normalized.y),
            previous_signed_distance_pixels=(previous_distance),
            signed_distance_pixels=(signed_distance_pixels),
            crossing_depth_pixels=(crossing_depth),
            velocity_x=track.velocity_x,
            velocity_y=track.velocity_y,
            speed_pixels_per_second=speed,
            direction_cosine=(direction_cosine),
            detection_confidence=(track.confidence),
            rule_confidence=(rule_confidence),
            is_violation=is_violation,
        )

    def _expire_missing_states(self) -> None:
        """Remove track-line states absent for too long."""

        for key, state in list(self._states.items()):
            if state.observed_this_frame:
                continue

            state.missed_frames += 1

            if state.missed_frames > self.maximum_missed_frames:
                del self._states[key]

    @staticmethod
    def _road_anchor_pixel(
        track: TrackedObject,
    ) -> PixelPointFloat:
        """Return the lower-center vehicle road anchor."""

        center_x, _ = track.bounding_box.center

        anchor_y = track.bounding_box.y1 + track.bounding_box.height * 0.90

        return (
            float(center_x),
            float(anchor_y),
        )

    @staticmethod
    def _road_anchor_normalized(
        *,
        anchor_pixel: PixelPointFloat,
        image_width: int,
        image_height: int,
    ) -> NormalizedPoint:
        """Convert a road anchor to normalized coordinates."""

        denominator_x = max(
            image_width - 1,
            1,
        )

        denominator_y = max(
            image_height - 1,
            1,
        )

        return NormalizedPoint(
            x=min(
                max(
                    anchor_pixel[0] / denominator_x,
                    0.0,
                ),
                1.0,
            ),
            y=min(
                max(
                    anchor_pixel[1] / denominator_y,
                    0.0,
                ),
                1.0,
            ),
        )

    @staticmethod
    def _legal_direction_sign(
        *,
        lane: LaneConfiguration,
        stop_line_pixels: tuple[
            tuple[int, int],
            tuple[int, int],
        ],
        image_width: int,
        image_height: int,
    ) -> float | None:
        """
        Return the sign that makes legal travel increase distance.

        The lane direction is scaled into pixel coordinates because
        normalized x and y axes can represent different pixel lengths.
        """

        line_start, line_end = stop_line_pixels

        line_x = line_end[0] - line_start[0]

        line_y = line_end[1] - line_start[1]

        direction_x = lane.allowed_direction.x * max(
            image_width - 1,
            1,
        )

        direction_y = lane.allowed_direction.y * max(
            image_height - 1,
            1,
        )

        direction_side = line_x * direction_y - line_y * direction_x

        if abs(direction_side) < 0.000001:
            return None

        return 1.0 if direction_side > 0.0 else -1.0

    @staticmethod
    def _signed_distance_to_line(
        *,
        point: PixelPointFloat,
        line_start: tuple[int, int],
        line_end: tuple[int, int],
    ) -> float:
        """Return perpendicular signed distance to an infinite line."""

        line_x = line_end[0] - line_start[0]

        line_y = line_end[1] - line_start[1]

        line_length = hypot(
            line_x,
            line_y,
        )

        if line_length == 0.0:
            return 0.0

        point_x = point[0] - line_start[0]

        point_y = point[1] - line_start[1]

        return (line_x * point_y - line_y * point_x) / line_length

    @staticmethod
    def _direction_cosine(
        *,
        track: TrackedObject,
        lane: LaneConfiguration,
        image_width: int,
        image_height: int,
    ) -> float:
        """Compare vehicle velocity with the lane's allowed direction."""

        speed = hypot(
            track.velocity_x,
            track.velocity_y,
        )

        if speed == 0.0:
            return 0.0

        direction_x = lane.allowed_direction.x * max(
            image_width - 1,
            1,
        )

        direction_y = lane.allowed_direction.y * max(
            image_height - 1,
            1,
        )

        direction_magnitude = hypot(
            direction_x,
            direction_y,
        )

        if direction_magnitude == 0.0:
            return 0.0

        cosine = (track.velocity_x * direction_x + track.velocity_y * direction_y) / (
            speed * direction_magnitude
        )

        return min(
            max(
                cosine,
                -1.0,
            ),
            1.0,
        )

    @staticmethod
    def _segments_intersect(
        *,
        first_start: PixelPointFloat,
        first_end: PixelPointFloat,
        second_start: tuple[int, int],
        second_end: tuple[int, int],
    ) -> bool:
        """Return whether two finite line segments intersect."""

        first_vector = (
            first_end[0] - first_start[0],
            first_end[1] - first_start[1],
        )

        second_vector = (
            second_end[0] - second_start[0],
            second_end[1] - second_start[1],
        )

        denominator = (
            first_vector[0] * second_vector[1] - first_vector[1] * second_vector[0]
        )

        if abs(denominator) < 0.000001:
            return False

        offset = (
            second_start[0] - first_start[0],
            second_start[1] - first_start[1],
        )

        first_parameter = (
            offset[0] * second_vector[1] - offset[1] * second_vector[0]
        ) / denominator

        second_parameter = (
            offset[0] * first_vector[1] - offset[1] * first_vector[0]
        ) / denominator

        tolerance = 0.000001

        return (
            -tolerance <= first_parameter <= 1.0 + tolerance
            and -tolerance <= second_parameter <= 1.0 + tolerance
        )

    @staticmethod
    def _eligible_track(
        track: TrackedObject,
    ) -> bool:
        """Return whether a track can cross a stop line."""

        return (
            track.confirmed
            and track.missed_frames == 0
            and track.class_name in VEHICLE_CLASS_NAMES
        )

    @staticmethod
    def _create_transition(
        observation: RedLightCrossingObservation,
    ) -> RedLightViolationTransition:
        """Convert a violating crossing to a lifecycle transition."""

        return RedLightViolationTransition(
            transition_type=(RedLightTransitionType.STARTED),
            track_id=observation.track_id,
            class_name=(observation.class_name),
            stop_line_id=(observation.stop_line_id),
            lane_id=observation.lane_id,
            traffic_light_region_id=(observation.traffic_light_region_id),
            signal_state=(observation.signal_state),
            signal_confidence=(observation.signal_confidence),
            previous_frame_number=(observation.previous_frame_number),
            frame_number=(observation.frame_number),
            timestamp_seconds=(observation.timestamp_seconds),
            previous_anchor_x_normalized=(observation.previous_anchor_x_normalized),
            previous_anchor_y_normalized=(observation.previous_anchor_y_normalized),
            anchor_x_normalized=(observation.anchor_x_normalized),
            anchor_y_normalized=(observation.anchor_y_normalized),
            previous_signed_distance_pixels=(
                observation.previous_signed_distance_pixels
            ),
            signed_distance_pixels=(observation.signed_distance_pixels),
            crossing_depth_pixels=(observation.crossing_depth_pixels),
            velocity_x=(observation.velocity_x),
            velocity_y=(observation.velocity_y),
            speed_pixels_per_second=(observation.speed_pixels_per_second),
            direction_cosine=(observation.direction_cosine),
            detection_confidence=(observation.detection_confidence),
            rule_confidence=(observation.rule_confidence),
        )

    @staticmethod
    def _clamp01(
        value: float,
    ) -> float:
        return min(
            max(
                value,
                0.0,
            ),
            1.0,
        )
