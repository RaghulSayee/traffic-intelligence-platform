from __future__ import annotations

from dataclasses import dataclass

from app.reasoning.traffic_light_state import (
    TrafficLightObservation,
    TrafficLightState,
    TrafficLightStateResult,
)


@dataclass(frozen=True, slots=True)
class StableTrafficLightSnapshot:
    """Stable temporal state for one configured signal region."""

    region_id: str
    region_name: str | None

    raw_state: TrafficLightState
    raw_confidence: float

    stable_state: TrafficLightState
    stable_confidence: float

    candidate_state: TrafficLightState
    candidate_confidence: float
    consecutive_candidate_frames: int

    unknown_frames: int

    red_score: float
    yellow_score: float
    green_score: float
    active_pixel_ratio: float

    last_observed_frame: int
    observed_this_frame: bool


@dataclass(frozen=True, slots=True)
class TrafficLightStateTransition:
    """A confirmed traffic-light state change."""

    region_id: str
    region_name: str | None

    previous_state: TrafficLightState
    current_state: TrafficLightState

    confidence: float

    frame_number: int
    timestamp_seconds: float

    confirmation_frames: int


@dataclass(frozen=True, slots=True)
class StableTrafficLightResult:
    """Temporal signal states and confirmed transitions."""

    states: tuple[
        StableTrafficLightSnapshot,
        ...,
    ]

    transitions: tuple[
        TrafficLightStateTransition,
        ...,
    ] = ()

    def get_region(
        self,
        region_id: str,
    ) -> StableTrafficLightSnapshot | None:
        """Return a stable signal state by region ID."""

        for state in self.states:
            if state.region_id == region_id:
                return state

        return None

    def count_by_stable_state(
        self,
    ) -> dict[str, int]:
        """Count configured regions by stable state."""

        counts: dict[str, int] = {}

        for state in self.states:
            key = state.stable_state.value

            counts[key] = (
                counts.get(
                    key,
                    0,
                )
                + 1
            )

        return counts


@dataclass(slots=True)
class _TrafficLightTemporalState:
    """Mutable temporal state for one signal region."""

    region_id: str
    region_name: str | None

    raw_state: TrafficLightState
    raw_confidence: float

    stable_state: TrafficLightState
    stable_confidence: float

    candidate_state: TrafficLightState
    candidate_confidence: float
    consecutive_candidate_frames: int

    unknown_frames: int

    red_score: float
    yellow_score: float
    green_score: float
    active_pixel_ratio: float

    last_observed_frame: int
    observed_this_frame: bool

    def to_public(
        self,
    ) -> StableTrafficLightSnapshot:
        """Return an immutable public snapshot."""

        return StableTrafficLightSnapshot(
            region_id=self.region_id,
            region_name=self.region_name,
            raw_state=self.raw_state,
            raw_confidence=self.raw_confidence,
            stable_state=self.stable_state,
            stable_confidence=(self.stable_confidence),
            candidate_state=self.candidate_state,
            candidate_confidence=(self.candidate_confidence),
            consecutive_candidate_frames=(self.consecutive_candidate_frames),
            unknown_frames=self.unknown_frames,
            red_score=self.red_score,
            yellow_score=self.yellow_score,
            green_score=self.green_score,
            active_pixel_ratio=(self.active_pixel_ratio),
            last_observed_frame=(self.last_observed_frame),
            observed_this_frame=(self.observed_this_frame),
        )


class TrafficLightTemporalStabilizer:
    """
    Stabilize frame-level traffic-light classifications.

    A new visible color must remain consistent for several analyzed
    frames before replacing the stable state.

    Brief UNKNOWN classifications preserve the previous stable state.
    A prolonged UNKNOWN period moves the stable state to UNKNOWN.
    """

    def __init__(
        self,
        *,
        confirmation_frames: int,
        maximum_unknown_frames: int,
        confidence_alpha: float,
    ) -> None:
        if confirmation_frames <= 0:
            raise ValueError("Confirmation frames must be positive.")

        if maximum_unknown_frames < 0:
            raise ValueError("Maximum unknown frames cannot be negative.")

        if not 0.0 < confidence_alpha <= 1.0:
            raise ValueError(
                "Confidence alpha must be greater than zero and at most one."
            )

        self.confirmation_frames = confirmation_frames
        self.maximum_unknown_frames = maximum_unknown_frames

        self.confidence_alpha = confidence_alpha

        self._states: dict[
            str,
            _TrafficLightTemporalState,
        ] = {}

    def update(
        self,
        *,
        frame_number: int,
        timestamp_seconds: float,
        observations: TrafficLightStateResult,
    ) -> StableTrafficLightResult:
        """Update stable signal states for one analyzed frame."""

        if frame_number <= 0:
            raise ValueError("Frame number must be positive.")

        if timestamp_seconds < 0:
            raise ValueError("Timestamp cannot be negative.")

        for state in self._states.values():
            state.observed_this_frame = False

        transitions: list[TrafficLightStateTransition] = []

        observed_region_ids = set()

        for observation in observations.observations:
            observed_region_ids.add(observation.region_id)

            state = self._states.get(observation.region_id)

            if state is None:
                state = self._create_state(
                    observation=observation,
                    frame_number=frame_number,
                )

                self._states[observation.region_id] = state

            transition = self._apply_observation(
                state=state,
                observation=observation,
                frame_number=frame_number,
                timestamp_seconds=timestamp_seconds,
            )

            if transition is not None:
                transitions.append(transition)

        for region_id, state in self._states.items():
            if region_id in observed_region_ids:
                continue

            transition = self._apply_unknown(
                state=state,
                frame_number=frame_number,
                timestamp_seconds=timestamp_seconds,
                observed_this_frame=False,
            )

            if transition is not None:
                transitions.append(transition)

        public_states = tuple(
            state.to_public() for _, state in sorted(self._states.items())
        )

        return StableTrafficLightResult(
            states=public_states,
            transitions=tuple(transitions),
        )

    def reset(self) -> None:
        """Clear all signal state before another video."""

        self._states.clear()

    def _apply_observation(
        self,
        *,
        state: _TrafficLightTemporalState,
        observation: TrafficLightObservation,
        frame_number: int,
        timestamp_seconds: float,
    ) -> TrafficLightStateTransition | None:
        """Apply one raw region classification."""

        state.region_name = observation.region_name

        state.raw_state = observation.state
        state.raw_confidence = observation.confidence

        state.red_score = observation.red_score
        state.yellow_score = observation.yellow_score
        state.green_score = observation.green_score

        state.active_pixel_ratio = observation.active_pixel_ratio

        state.last_observed_frame = frame_number
        state.observed_this_frame = True

        if observation.state == TrafficLightState.UNKNOWN:
            return self._apply_unknown(
                state=state,
                frame_number=frame_number,
                timestamp_seconds=timestamp_seconds,
                observed_this_frame=True,
            )

        state.unknown_frames = 0

        if observation.state == state.stable_state:
            state.stable_confidence = self._smooth_confidence(
                previous=state.stable_confidence,
                current=observation.confidence,
            )

            self._clear_candidate(state)

            return None

        if observation.state == state.candidate_state:
            state.consecutive_candidate_frames += 1

            state.candidate_confidence = self._smooth_confidence(
                previous=(state.candidate_confidence),
                current=observation.confidence,
            )

        else:
            state.candidate_state = observation.state

            state.candidate_confidence = observation.confidence

            state.consecutive_candidate_frames = 1

        if state.consecutive_candidate_frames < self.confirmation_frames:
            return None

        previous_state = state.stable_state

        state.stable_state = state.candidate_state

        state.stable_confidence = state.candidate_confidence

        confirmation_count = state.consecutive_candidate_frames

        self._clear_candidate(state)

        return TrafficLightStateTransition(
            region_id=state.region_id,
            region_name=state.region_name,
            previous_state=previous_state,
            current_state=state.stable_state,
            confidence=state.stable_confidence,
            frame_number=frame_number,
            timestamp_seconds=timestamp_seconds,
            confirmation_frames=confirmation_count,
        )

    def _apply_unknown(
        self,
        *,
        state: _TrafficLightTemporalState,
        frame_number: int,
        timestamp_seconds: float,
        observed_this_frame: bool,
    ) -> TrafficLightStateTransition | None:
        """Handle an unknown or missing region observation."""

        state.raw_state = TrafficLightState.UNKNOWN
        state.raw_confidence = 0.0

        state.observed_this_frame = observed_this_frame
        state.unknown_frames += 1

        self._clear_candidate(state)

        if state.unknown_frames <= self.maximum_unknown_frames:
            return None

        if state.stable_state == TrafficLightState.UNKNOWN:
            state.stable_confidence = 0.0
            return None

        previous_state = state.stable_state

        state.stable_state = TrafficLightState.UNKNOWN
        state.stable_confidence = 0.0

        return TrafficLightStateTransition(
            region_id=state.region_id,
            region_name=state.region_name,
            previous_state=previous_state,
            current_state=TrafficLightState.UNKNOWN,
            confidence=0.0,
            frame_number=frame_number,
            timestamp_seconds=timestamp_seconds,
            confirmation_frames=(state.unknown_frames),
        )

    def _smooth_confidence(
        self,
        *,
        previous: float,
        current: float,
    ) -> float:
        """Apply an exponential moving average."""

        return (
            self.confidence_alpha * current + (1.0 - self.confidence_alpha) * previous
        )

    @staticmethod
    def _create_state(
        *,
        observation: TrafficLightObservation,
        frame_number: int,
    ) -> _TrafficLightTemporalState:
        """Create initial UNKNOWN stable state."""

        return _TrafficLightTemporalState(
            region_id=observation.region_id,
            region_name=observation.region_name,
            raw_state=TrafficLightState.UNKNOWN,
            raw_confidence=0.0,
            stable_state=TrafficLightState.UNKNOWN,
            stable_confidence=0.0,
            candidate_state=TrafficLightState.UNKNOWN,
            candidate_confidence=0.0,
            consecutive_candidate_frames=0,
            unknown_frames=0,
            red_score=0.0,
            yellow_score=0.0,
            green_score=0.0,
            active_pixel_ratio=0.0,
            last_observed_frame=frame_number,
            observed_this_frame=False,
        )

    @staticmethod
    def _clear_candidate(
        state: _TrafficLightTemporalState,
    ) -> None:
        """Clear an unconfirmed color candidate."""

        state.candidate_state = TrafficLightState.UNKNOWN

        state.candidate_confidence = 0.0

        state.consecutive_candidate_frames = 0
