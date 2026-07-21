from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import hypot

from app.models.enums import ViolationType
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
    LaneConfiguration,
    NormalizedPoint,
)
from app.scene.geometry import (
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


WrongWayStateKey = tuple[int, str]


class WrongWayTransitionType(StrEnum):
    """Lifecycle transitions emitted for wrong-way movement."""

    STARTED = "started"
    ENDED = "ended"


@dataclass(frozen=True, slots=True)
class WrongWayViolationSnapshot:
    """Current wrong-way state for one tracked vehicle."""

    track_id: int
    class_name: str
    lane_id: str

    velocity_x: float
    velocity_y: float
    speed_pixels_per_second: float

    cosine_similarity: float
    opposition_score: float

    first_candidate_frame: int
    confirmed_frame: int | None
    last_violation_frame: int

    consecutive_violation_frames: int
    missed_frames: int

    confirmed: bool
    observed_this_frame: bool


@dataclass(frozen=True, slots=True)
class WrongWayTransition:
    """An important wrong-way lifecycle transition."""

    transition_type: WrongWayTransitionType

    track_id: int
    class_name: str
    lane_id: str

    velocity_x: float
    velocity_y: float
    speed_pixels_per_second: float

    cosine_similarity: float
    opposition_score: float

    frame_number: int
    timestamp_seconds: float

    first_candidate_frame: int
    confirmed_frame: int | None

    duration_seconds: float


@dataclass(frozen=True, slots=True)
class WrongWayDetectionResult:
    """Wrong-way states produced for one analyzed frame."""

    states: tuple[
        WrongWayViolationSnapshot,
        ...,
    ]

    transitions: tuple[
        WrongWayTransition,
        ...,
    ] = ()

    @property
    def active_violations(
        self,
    ) -> tuple[
        WrongWayViolationSnapshot,
        ...,
    ]:
        """Return confirmed wrong-way violations."""

        return tuple(state for state in self.states if state.confirmed)


@dataclass(frozen=True, slots=True)
class _WrongWayObservation:
    """One vehicle moving against its configured lane."""

    track_id: int
    class_name: str
    lane_id: str

    velocity_x: float
    velocity_y: float
    speed_pixels_per_second: float

    cosine_similarity: float
    opposition_score: float


@dataclass(slots=True)
class _WrongWayState:
    """Mutable temporal state for one track and lane."""

    track_id: int
    class_name: str
    lane_id: str

    velocity_x: float
    velocity_y: float
    speed_pixels_per_second: float

    cosine_similarity: float
    opposition_score: float

    first_candidate_frame: int
    first_candidate_timestamp: float

    confirmed_frame: int | None
    confirmed_timestamp: float | None

    last_violation_frame: int
    last_violation_timestamp: float

    consecutive_violation_frames: int
    missed_frames: int

    confirmed: bool
    observed_this_frame: bool

    def to_public(
        self,
    ) -> WrongWayViolationSnapshot:
        """Create an immutable public snapshot."""

        return WrongWayViolationSnapshot(
            track_id=self.track_id,
            class_name=self.class_name,
            lane_id=self.lane_id,
            velocity_x=self.velocity_x,
            velocity_y=self.velocity_y,
            speed_pixels_per_second=(self.speed_pixels_per_second),
            cosine_similarity=(self.cosine_similarity),
            opposition_score=self.opposition_score,
            first_candidate_frame=(self.first_candidate_frame),
            confirmed_frame=self.confirmed_frame,
            last_violation_frame=(self.last_violation_frame),
            consecutive_violation_frames=(self.consecutive_violation_frames),
            missed_frames=self.missed_frames,
            confirmed=self.confirmed,
            observed_this_frame=(self.observed_this_frame),
        )


class WrongWayViolationDetector:
    """
    Detect vehicles moving against their configured lane direction.

    A vehicle must:
    1. Be a visible confirmed vehicle track.
    2. Have its lower-center anchor inside a configured lane.
    3. Be moving faster than the minimum speed.
    4. Have a direction cosine below the configured threshold.
    5. Remain wrong-way for several analyzed frames.
    """

    def __init__(
        self,
        *,
        minimum_speed_pixels_per_second: float,
        opposite_cosine_threshold: float,
        confirmation_frames: int,
        maximum_missed_frames: int,
    ) -> None:
        if minimum_speed_pixels_per_second < 0:
            raise ValueError("Minimum speed cannot be negative.")

        if not -1.0 <= opposite_cosine_threshold < 0.0:
            raise ValueError(
                "Opposite cosine threshold must be at least -1 and less than zero."
            )

        if confirmation_frames <= 0:
            raise ValueError("Confirmation frames must be positive.")

        if maximum_missed_frames < 0:
            raise ValueError("Maximum missed frames cannot be negative.")

        self.minimum_speed_pixels_per_second = minimum_speed_pixels_per_second

        self.opposite_cosine_threshold = opposite_cosine_threshold

        self.confirmation_frames = confirmation_frames

        self.maximum_missed_frames = maximum_missed_frames

        self._states: dict[
            WrongWayStateKey,
            _WrongWayState,
        ] = {}

    def update(
        self,
        *,
        frame_number: int,
        timestamp_seconds: float,
        tracks: tuple[TrackedObject, ...],
        scene: CameraSceneConfiguration | None,
        image_width: int,
        image_height: int,
    ) -> WrongWayDetectionResult:
        """Update wrong-way states using one analyzed frame."""

        if frame_number <= 0:
            raise ValueError("Frame number must be positive.")

        if timestamp_seconds < 0:
            raise ValueError("Timestamp cannot be negative.")

        if image_width <= 0 or image_height <= 0:
            raise ValueError("Image dimensions must be positive.")

        observations = self._find_observations(
            tracks=tracks,
            scene=scene,
            image_width=image_width,
            image_height=image_height,
        )

        observed_by_key = {
            (
                observation.track_id,
                observation.lane_id,
            ): observation
            for observation in observations
        }

        for state in self._states.values():
            state.observed_this_frame = False

        transitions: list[WrongWayTransition] = []

        for key, observation in observed_by_key.items():
            state = self._states.get(key)

            if state is None:
                state = _WrongWayState(
                    track_id=observation.track_id,
                    class_name=observation.class_name,
                    lane_id=observation.lane_id,
                    velocity_x=observation.velocity_x,
                    velocity_y=observation.velocity_y,
                    speed_pixels_per_second=(observation.speed_pixels_per_second),
                    cosine_similarity=(observation.cosine_similarity),
                    opposition_score=(observation.opposition_score),
                    first_candidate_frame=frame_number,
                    first_candidate_timestamp=(timestamp_seconds),
                    confirmed_frame=None,
                    confirmed_timestamp=None,
                    last_violation_frame=frame_number,
                    last_violation_timestamp=(timestamp_seconds),
                    consecutive_violation_frames=1,
                    missed_frames=0,
                    confirmed=False,
                    observed_this_frame=True,
                )

                self._states[key] = state

            else:
                state.velocity_x = observation.velocity_x
                state.velocity_y = observation.velocity_y

                state.speed_pixels_per_second = observation.speed_pixels_per_second

                state.cosine_similarity = observation.cosine_similarity

                state.opposition_score = max(
                    state.opposition_score,
                    observation.opposition_score,
                )

                state.last_violation_frame = frame_number

                state.last_violation_timestamp = timestamp_seconds

                state.consecutive_violation_frames += 1

                state.missed_frames = 0
                state.observed_this_frame = True

            if (
                not state.confirmed
                and state.consecutive_violation_frames >= self.confirmation_frames
            ):
                state.confirmed = True
                state.confirmed_frame = frame_number

                state.confirmed_timestamp = timestamp_seconds

                transitions.append(
                    self._create_transition(
                        state=state,
                        transition_type=(WrongWayTransitionType.STARTED),
                        frame_number=frame_number,
                        timestamp_seconds=(timestamp_seconds),
                    )
                )

        for key, state in list(self._states.items()):
            if key in observed_by_key:
                continue

            state.observed_this_frame = False
            state.missed_frames += 1

            state.consecutive_violation_frames = 0

            if state.missed_frames <= self.maximum_missed_frames:
                continue

            if state.confirmed:
                transitions.append(
                    self._create_transition(
                        state=state,
                        transition_type=(WrongWayTransitionType.ENDED),
                        frame_number=frame_number,
                        timestamp_seconds=(timestamp_seconds),
                    )
                )

            del self._states[key]

        public_states = tuple(
            state.to_public() for _, state in sorted(self._states.items())
        )

        return WrongWayDetectionResult(
            states=public_states,
            transitions=tuple(transitions),
        )

    def flush(
        self,
        *,
        frame_number: int,
        timestamp_seconds: float,
    ) -> tuple[WrongWayTransition, ...]:
        """
        End confirmed violations when video processing stops.

        Unconfirmed candidates are discarded because they never
        satisfied the temporal confirmation requirement.
        """

        if frame_number <= 0:
            raise ValueError("Frame number must be positive.")

        if timestamp_seconds < 0:
            raise ValueError("Timestamp cannot be negative.")

        transitions = tuple(
            self._create_transition(
                state=state,
                transition_type=(WrongWayTransitionType.ENDED),
                frame_number=frame_number,
                timestamp_seconds=timestamp_seconds,
            )
            for _, state in sorted(self._states.items())
            if state.confirmed
        )

        self._states.clear()

        return transitions

    def reset(self) -> None:
        """Clear all state before another video."""

        self._states.clear()

    def _find_observations(
        self,
        *,
        tracks: tuple[TrackedObject, ...],
        scene: CameraSceneConfiguration | None,
        image_width: int,
        image_height: int,
    ) -> tuple[_WrongWayObservation, ...]:
        """Find visible tracks moving against lane direction."""

        if (
            scene is None
            or ViolationType.WRONG_WAY not in scene.enabled_violations
            or not scene.lanes
        ):
            return ()

        observations: list[_WrongWayObservation] = []

        for track in tracks:
            if not self._eligible_track(track):
                continue

            lane = self._find_lane(
                track=track,
                lanes=scene.lanes,
                image_width=image_width,
                image_height=image_height,
            )

            if lane is None:
                continue

            observation = self._score_direction(
                track=track,
                lane=lane,
            )

            if observation is not None:
                observations.append(observation)

        return tuple(observations)

    def _score_direction(
        self,
        *,
        track: TrackedObject,
        lane: LaneConfiguration,
    ) -> _WrongWayObservation | None:
        speed = hypot(
            track.velocity_x,
            track.velocity_y,
        )

        if speed < self.minimum_speed_pixels_per_second:
            return None

        lane_magnitude = hypot(
            lane.allowed_direction.x,
            lane.allowed_direction.y,
        )

        cosine_similarity = (
            track.velocity_x * lane.allowed_direction.x
            + track.velocity_y * lane.allowed_direction.y
        ) / (speed * lane_magnitude)

        cosine_similarity = min(
            max(cosine_similarity, -1.0),
            1.0,
        )

        if cosine_similarity > self.opposite_cosine_threshold:
            return None

        opposition_score = min(
            max(-cosine_similarity, 0.0),
            1.0,
        )

        return _WrongWayObservation(
            track_id=track.track_id,
            class_name=track.class_name,
            lane_id=lane.lane_id,
            velocity_x=track.velocity_x,
            velocity_y=track.velocity_y,
            speed_pixels_per_second=speed,
            cosine_similarity=cosine_similarity,
            opposition_score=opposition_score,
        )

    @staticmethod
    def _find_lane(
        *,
        track: TrackedObject,
        lanes: list[LaneConfiguration],
        image_width: int,
        image_height: int,
    ) -> LaneConfiguration | None:
        """Find the first lane containing the vehicle road anchor."""

        denominator_x = max(
            image_width - 1,
            1,
        )

        denominator_y = max(
            image_height - 1,
            1,
        )

        center_x, _ = track.bounding_box.center

        road_anchor_y = track.bounding_box.y1 + track.bounding_box.height * 0.90

        normalized_anchor = NormalizedPoint(
            x=min(
                max(
                    center_x / denominator_x,
                    0.0,
                ),
                1.0,
            ),
            y=min(
                max(
                    road_anchor_y / denominator_y,
                    0.0,
                ),
                1.0,
            ),
        )

        for lane in lanes:
            if normalized_point_in_polygon(
                point=normalized_anchor,
                polygon=lane.polygon,
            ):
                return lane

        return None

    @staticmethod
    def _eligible_track(
        track: TrackedObject,
    ) -> bool:
        return (
            track.confirmed
            and track.missed_frames == 0
            and track.class_name in VEHICLE_CLASS_NAMES
        )

    @staticmethod
    def _create_transition(
        *,
        state: _WrongWayState,
        transition_type: WrongWayTransitionType,
        frame_number: int,
        timestamp_seconds: float,
    ) -> WrongWayTransition:
        duration_seconds = 0.0

        if state.confirmed_timestamp is not None:
            duration_seconds = max(
                timestamp_seconds - state.confirmed_timestamp,
                0.0,
            )

        return WrongWayTransition(
            transition_type=transition_type,
            track_id=state.track_id,
            class_name=state.class_name,
            lane_id=state.lane_id,
            velocity_x=state.velocity_x,
            velocity_y=state.velocity_y,
            speed_pixels_per_second=(state.speed_pixels_per_second),
            cosine_similarity=(state.cosine_similarity),
            opposition_score=state.opposition_score,
            frame_number=frame_number,
            timestamp_seconds=timestamp_seconds,
            first_candidate_frame=(state.first_candidate_frame),
            confirmed_frame=state.confirmed_frame,
            duration_seconds=duration_seconds,
        )
