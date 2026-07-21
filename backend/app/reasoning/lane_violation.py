from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.reasoning.lane_occupancy import (
    LaneOccupancyAnalyzer,
    LaneOccupancyObservation,
    LaneOccupancyResult,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)
from app.tracking.types import TrackedObject


LaneViolationStateKey = int


class LaneViolationTransitionType(StrEnum):
    """Lifecycle transitions for lane violations."""

    STARTED = "started"
    ENDED = "ended"


@dataclass(frozen=True, slots=True)
class LaneViolationSnapshot:
    """Current lane-violation state for one vehicle."""

    track_id: int
    class_name: str

    nearest_lane_id: str | None

    anchor_x_normalized: float
    anchor_y_normalized: float

    distance_to_nearest_lane_pixels: float | None

    velocity_x: float
    velocity_y: float
    speed_pixels_per_second: float

    first_candidate_frame: int
    confirmed_frame: int | None
    last_violation_frame: int

    consecutive_violation_frames: int
    missed_frames: int

    confirmed: bool
    observed_this_frame: bool


@dataclass(frozen=True, slots=True)
class LaneViolationTransition:
    """Important lane-violation lifecycle transition."""

    transition_type: LaneViolationTransitionType

    track_id: int
    class_name: str

    nearest_lane_id: str | None

    anchor_x_normalized: float
    anchor_y_normalized: float

    distance_to_nearest_lane_pixels: float | None

    velocity_x: float
    velocity_y: float
    speed_pixels_per_second: float

    frame_number: int
    timestamp_seconds: float

    first_candidate_frame: int
    confirmed_frame: int | None

    duration_seconds: float


@dataclass(frozen=True, slots=True)
class LaneViolationDetectionResult:
    """Lane-violation states produced for one frame."""

    occupancy: LaneOccupancyResult

    states: tuple[
        LaneViolationSnapshot,
        ...,
    ]

    transitions: tuple[
        LaneViolationTransition,
        ...,
    ] = ()

    @property
    def active_violations(
        self,
    ) -> tuple[
        LaneViolationSnapshot,
        ...,
    ]:
        """Return confirmed lane violations."""

        return tuple(state for state in self.states if state.confirmed)


@dataclass(slots=True)
class _LaneViolationState:
    """Mutable temporal state for one vehicle."""

    track_id: int
    class_name: str

    nearest_lane_id: str | None

    anchor_x_normalized: float
    anchor_y_normalized: float

    distance_to_nearest_lane_pixels: float | None

    velocity_x: float
    velocity_y: float
    speed_pixels_per_second: float

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
    ) -> LaneViolationSnapshot:
        """Create an immutable public snapshot."""

        return LaneViolationSnapshot(
            track_id=self.track_id,
            class_name=self.class_name,
            nearest_lane_id=self.nearest_lane_id,
            anchor_x_normalized=(self.anchor_x_normalized),
            anchor_y_normalized=(self.anchor_y_normalized),
            distance_to_nearest_lane_pixels=(self.distance_to_nearest_lane_pixels),
            velocity_x=self.velocity_x,
            velocity_y=self.velocity_y,
            speed_pixels_per_second=(self.speed_pixels_per_second),
            first_candidate_frame=(self.first_candidate_frame),
            confirmed_frame=self.confirmed_frame,
            last_violation_frame=(self.last_violation_frame),
            consecutive_violation_frames=(self.consecutive_violation_frames),
            missed_frames=self.missed_frames,
            confirmed=self.confirmed,
            observed_this_frame=(self.observed_this_frame),
        )


class LaneViolationDetector:
    """
    Confirm sustained movement outside configured lanes.

    A violation begins after a vehicle remains a lane-occupancy
    candidate for the required number of analyzed frames.

    A confirmed violation ends after the vehicle is no longer a
    candidate for more than the allowed missed-frame tolerance.
    """

    def __init__(
        self,
        *,
        occupancy_analyzer: LaneOccupancyAnalyzer,
        confirmation_frames: int,
        maximum_missed_frames: int,
    ) -> None:
        if confirmation_frames <= 0:
            raise ValueError("Confirmation frames must be positive.")

        if maximum_missed_frames < 0:
            raise ValueError("Maximum missed frames cannot be negative.")

        self.occupancy_analyzer = occupancy_analyzer

        self.confirmation_frames = confirmation_frames

        self.maximum_missed_frames = maximum_missed_frames

        self._states: dict[
            LaneViolationStateKey,
            _LaneViolationState,
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
    ) -> LaneViolationDetectionResult:
        """Update lane-violation states for one frame."""

        if frame_number <= 0:
            raise ValueError("Frame number must be positive.")

        if timestamp_seconds < 0:
            raise ValueError("Timestamp cannot be negative.")

        occupancy = self.occupancy_analyzer.analyze(
            tracks=tracks,
            scene=scene,
            image_width=image_width,
            image_height=image_height,
        )

        candidates_by_track = {
            observation.track_id: observation
            for observation in occupancy.violation_candidates
        }

        for state in self._states.values():
            state.observed_this_frame = False

        transitions: list[LaneViolationTransition] = []

        for (
            track_id,
            observation,
        ) in candidates_by_track.items():
            state = self._states.get(track_id)

            if state is None:
                state = self._create_state(
                    observation=observation,
                    frame_number=frame_number,
                    timestamp_seconds=(timestamp_seconds),
                )

                self._states[track_id] = state

            else:
                self._update_state(
                    state=state,
                    observation=observation,
                    frame_number=frame_number,
                    timestamp_seconds=(timestamp_seconds),
                )

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
                        transition_type=(LaneViolationTransitionType.STARTED),
                        frame_number=(frame_number),
                        timestamp_seconds=(timestamp_seconds),
                    )
                )

        for (
            track_id,
            state,
        ) in list(self._states.items()):
            if track_id in candidates_by_track:
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
                        transition_type=(LaneViolationTransitionType.ENDED),
                        frame_number=(frame_number),
                        timestamp_seconds=(timestamp_seconds),
                    )
                )

            del self._states[track_id]

        states = tuple(state.to_public() for _, state in sorted(self._states.items()))

        return LaneViolationDetectionResult(
            occupancy=occupancy,
            states=states,
            transitions=tuple(transitions),
        )

    def reset(self) -> None:
        """Clear state before processing another video."""

        self._states.clear()

    @staticmethod
    def _create_state(
        *,
        observation: LaneOccupancyObservation,
        frame_number: int,
        timestamp_seconds: float,
    ) -> _LaneViolationState:
        """Create state from the first candidate frame."""

        return _LaneViolationState(
            track_id=observation.track_id,
            class_name=observation.class_name,
            nearest_lane_id=(observation.nearest_lane_id),
            anchor_x_normalized=(observation.anchor_x_normalized),
            anchor_y_normalized=(observation.anchor_y_normalized),
            distance_to_nearest_lane_pixels=(
                observation.distance_to_nearest_lane_pixels
            ),
            velocity_x=observation.velocity_x,
            velocity_y=observation.velocity_y,
            speed_pixels_per_second=(observation.speed_pixels_per_second),
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

    @staticmethod
    def _update_state(
        *,
        state: _LaneViolationState,
        observation: LaneOccupancyObservation,
        frame_number: int,
        timestamp_seconds: float,
    ) -> None:
        """Update state using another candidate frame."""

        had_gap = state.missed_frames > 0

        if had_gap and not state.confirmed:
            state.first_candidate_frame = frame_number

            state.first_candidate_timestamp = timestamp_seconds

            state.consecutive_violation_frames = 1

        else:
            state.consecutive_violation_frames += 1

        state.class_name = observation.class_name

        state.nearest_lane_id = observation.nearest_lane_id

        state.anchor_x_normalized = observation.anchor_x_normalized

        state.anchor_y_normalized = observation.anchor_y_normalized

        state.distance_to_nearest_lane_pixels = (
            observation.distance_to_nearest_lane_pixels
        )

        state.velocity_x = observation.velocity_x

        state.velocity_y = observation.velocity_y

        state.speed_pixels_per_second = observation.speed_pixels_per_second

        state.last_violation_frame = frame_number

        state.last_violation_timestamp = timestamp_seconds

        state.missed_frames = 0
        state.observed_this_frame = True

    @staticmethod
    def _create_transition(
        *,
        state: _LaneViolationState,
        transition_type: (LaneViolationTransitionType),
        frame_number: int,
        timestamp_seconds: float,
    ) -> LaneViolationTransition:
        """Create an immutable lifecycle transition."""

        duration_seconds = 0.0

        if state.confirmed_timestamp is not None:
            duration_seconds = max(
                timestamp_seconds - state.confirmed_timestamp,
                0.0,
            )

        return LaneViolationTransition(
            transition_type=transition_type,
            track_id=state.track_id,
            class_name=state.class_name,
            nearest_lane_id=(state.nearest_lane_id),
            anchor_x_normalized=(state.anchor_x_normalized),
            anchor_y_normalized=(state.anchor_y_normalized),
            distance_to_nearest_lane_pixels=(state.distance_to_nearest_lane_pixels),
            velocity_x=state.velocity_x,
            velocity_y=state.velocity_y,
            speed_pixels_per_second=(state.speed_pixels_per_second),
            frame_number=frame_number,
            timestamp_seconds=(timestamp_seconds),
            first_candidate_frame=(state.first_candidate_frame),
            confirmed_frame=(state.confirmed_frame),
            duration_seconds=(duration_seconds),
        )
