from dataclasses import dataclass
from enum import StrEnum

from app.detection.helmet import (
    NO_HELMET_CLASS_NAME,
)
from app.reasoning.helmet_rider import (
    HelmetRiderAssociationResult,
)


class NoHelmetTransitionType(StrEnum):
    """Lifecycle transitions emitted by the detector."""

    STARTED = "started"
    ENDED = "ended"


@dataclass(frozen=True, slots=True)
class NoHelmetViolationSnapshot:
    """Current state of one rider's no-helmet candidate."""

    person_track_id: int
    motorcycle_track_id: int

    detection_confidence: float
    association_score: float

    first_candidate_frame: int
    confirmed_frame: int | None
    last_violation_frame: int

    consecutive_violation_frames: int
    missed_frames: int

    confirmed: bool
    observed_this_frame: bool


@dataclass(frozen=True, slots=True)
class NoHelmetTransition:
    """An important no-helmet lifecycle transition."""

    transition_type: NoHelmetTransitionType

    person_track_id: int
    motorcycle_track_id: int

    detection_confidence: float
    association_score: float

    frame_number: int
    timestamp_seconds: float

    first_candidate_frame: int
    confirmed_frame: int | None

    duration_seconds: float


@dataclass(frozen=True, slots=True)
class NoHelmetDetectionResult:
    """No-helmet states produced for one analyzed frame."""

    states: tuple[
        NoHelmetViolationSnapshot,
        ...,
    ]

    transitions: tuple[
        NoHelmetTransition,
        ...,
    ] = ()

    @property
    def active_violations(
        self,
    ) -> tuple[
        NoHelmetViolationSnapshot,
        ...,
    ]:
        """Return confirmed active no-helmet violations."""

        return tuple(state for state in self.states if state.confirmed)


@dataclass(slots=True)
class _NoHelmetState:
    """Mutable internal state for one person track."""

    person_track_id: int
    motorcycle_track_id: int

    detection_confidence: float
    association_score: float

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
    ) -> NoHelmetViolationSnapshot:
        """Create an immutable public snapshot."""

        return NoHelmetViolationSnapshot(
            person_track_id=(self.person_track_id),
            motorcycle_track_id=(self.motorcycle_track_id),
            detection_confidence=(self.detection_confidence),
            association_score=(self.association_score),
            first_candidate_frame=(self.first_candidate_frame),
            confirmed_frame=(self.confirmed_frame),
            last_violation_frame=(self.last_violation_frame),
            consecutive_violation_frames=(self.consecutive_violation_frames),
            missed_frames=self.missed_frames,
            confirmed=self.confirmed,
            observed_this_frame=(self.observed_this_frame),
        )


class NoHelmetViolationDetector:
    """
    Confirm no-helmet violations across analyzed frames.

    A candidate begins when a confirmed motorcycle rider receives a
    no-helmet detection. Short detection gaps are tolerated.
    """

    def __init__(
        self,
        *,
        confirmation_frames: int,
        maximum_missed_frames: int,
        confidence_alpha: float,
    ) -> None:
        if confirmation_frames <= 0:
            raise ValueError("Confirmation frames must be positive.")

        if maximum_missed_frames < 0:
            raise ValueError("Maximum missed frames cannot be negative.")

        if not 0.0 < confidence_alpha <= 1.0:
            raise ValueError(
                "Confidence alpha must be greater than zero and no greater than one."
            )

        self.confirmation_frames = confirmation_frames

        self.maximum_missed_frames = maximum_missed_frames

        self.confidence_alpha = confidence_alpha

        self._states: dict[
            int,
            _NoHelmetState,
        ] = {}

    def update(
        self,
        *,
        frame_number: int,
        timestamp_seconds: float,
        associations: HelmetRiderAssociationResult,
    ) -> NoHelmetDetectionResult:
        """Update violation state using one analyzed frame."""

        if frame_number <= 0:
            raise ValueError("Frame number must be positive.")

        if timestamp_seconds < 0:
            raise ValueError("Timestamp cannot be negative.")

        observed_no_helmet = {
            association.person_track_id: association
            for association in associations.associations
            if association.class_name == NO_HELMET_CLASS_NAME
        }

        for state in self._states.values():
            state.observed_this_frame = False

        transitions: list[NoHelmetTransition] = []

        updated_person_ids: set[int] = set()

        for (
            person_track_id,
            association,
        ) in observed_no_helmet.items():
            updated_person_ids.add(person_track_id)

            state = self._states.get(person_track_id)

            if state is None:
                state = _NoHelmetState(
                    person_track_id=(person_track_id),
                    motorcycle_track_id=(association.motorcycle_track_id),
                    detection_confidence=(association.detection_confidence),
                    association_score=(association.association_score),
                    first_candidate_frame=(frame_number),
                    first_candidate_timestamp=(timestamp_seconds),
                    confirmed_frame=None,
                    confirmed_timestamp=None,
                    last_violation_frame=(frame_number),
                    last_violation_timestamp=(timestamp_seconds),
                    consecutive_violation_frames=1,
                    missed_frames=0,
                    confirmed=False,
                    observed_this_frame=True,
                )

                self._states[person_track_id] = state

            else:
                alpha = self.confidence_alpha

                state.motorcycle_track_id = association.motorcycle_track_id

                state.detection_confidence = (
                    alpha * association.detection_confidence
                    + (1.0 - alpha) * state.detection_confidence
                )

                state.association_score = (
                    alpha * association.association_score
                    + (1.0 - alpha) * state.association_score
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
                        transition_type=(NoHelmetTransitionType.STARTED),
                        frame_number=(frame_number),
                        timestamp_seconds=(timestamp_seconds),
                    )
                )

        for (
            person_track_id,
            state,
        ) in list(self._states.items()):
            if person_track_id in updated_person_ids:
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
                        transition_type=(NoHelmetTransitionType.ENDED),
                        frame_number=(frame_number),
                        timestamp_seconds=(timestamp_seconds),
                    )
                )

            del self._states[person_track_id]

        public_states = tuple(
            state.to_public() for _, state in sorted(self._states.items())
        )

        return NoHelmetDetectionResult(
            states=public_states,
            transitions=tuple(transitions),
        )

    def reset(self) -> None:
        """Clear state before processing another video."""

        self._states.clear()

    @staticmethod
    def _create_transition(
        *,
        state: _NoHelmetState,
        transition_type: NoHelmetTransitionType,
        frame_number: int,
        timestamp_seconds: float,
    ) -> NoHelmetTransition:
        confirmed_timestamp = state.confirmed_timestamp

        duration_seconds = 0.0

        if confirmed_timestamp is not None:
            duration_seconds = max(
                timestamp_seconds - confirmed_timestamp,
                0.0,
            )

        return NoHelmetTransition(
            transition_type=transition_type,
            person_track_id=(state.person_track_id),
            motorcycle_track_id=(state.motorcycle_track_id),
            detection_confidence=(state.detection_confidence),
            association_score=(state.association_score),
            frame_number=frame_number,
            timestamp_seconds=timestamp_seconds,
            first_candidate_frame=(state.first_candidate_frame),
            confirmed_frame=(state.confirmed_frame),
            duration_seconds=duration_seconds,
        )
