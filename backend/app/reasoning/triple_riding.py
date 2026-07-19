from dataclasses import dataclass
from enum import StrEnum

from app.reasoning.temporal_rider import (
    TemporalRiderAssociation,
    TemporalRiderAssociationResult,
)


class TripleRidingTransitionType(StrEnum):
    """Lifecycle transitions emitted by the detector."""

    STARTED = "started"
    ENDED = "ended"


@dataclass(frozen=True, slots=True)
class TripleRidingViolationSnapshot:
    """Current state of one motorcycle's violation candidate."""

    motorcycle_track_id: int
    rider_track_ids: tuple[int, ...]

    rider_count: int
    peak_rider_count: int

    average_association_score: float

    first_candidate_frame: int
    confirmed_frame: int | None
    last_violation_frame: int

    consecutive_violation_frames: int
    missed_frames: int

    confirmed: bool
    observed_this_frame: bool


@dataclass(frozen=True, slots=True)
class TripleRidingTransition:
    """An important violation lifecycle transition."""

    transition_type: TripleRidingTransitionType

    motorcycle_track_id: int
    rider_track_ids: tuple[int, ...]

    rider_count: int
    peak_rider_count: int

    frame_number: int
    timestamp_seconds: float

    first_candidate_frame: int
    confirmed_frame: int | None

    duration_seconds: float


@dataclass(frozen=True, slots=True)
class TripleRidingDetectionResult:
    """Triple-riding state produced for one analyzed frame."""

    states: tuple[
        TripleRidingViolationSnapshot,
        ...,
    ]

    transitions: tuple[
        TripleRidingTransition,
        ...,
    ] = ()

    @property
    def active_violations(
        self,
    ) -> tuple[TripleRidingViolationSnapshot, ...]:
        """Return confirmed violations that are still active."""

        return tuple(state for state in self.states if state.confirmed)


@dataclass(slots=True)
class _TripleRidingState:
    """Mutable internal state for one motorcycle."""

    motorcycle_track_id: int
    rider_track_ids: tuple[int, ...]

    rider_count: int
    peak_rider_count: int

    average_association_score: float

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
    ) -> TripleRidingViolationSnapshot:
        """Create an immutable public snapshot."""

        return TripleRidingViolationSnapshot(
            motorcycle_track_id=(self.motorcycle_track_id),
            rider_track_ids=self.rider_track_ids,
            rider_count=self.rider_count,
            peak_rider_count=self.peak_rider_count,
            average_association_score=(self.average_association_score),
            first_candidate_frame=(self.first_candidate_frame),
            confirmed_frame=self.confirmed_frame,
            last_violation_frame=(self.last_violation_frame),
            consecutive_violation_frames=(self.consecutive_violation_frames),
            missed_frames=self.missed_frames,
            confirmed=self.confirmed,
            observed_this_frame=(self.observed_this_frame),
        )


class TripleRidingViolationDetector:
    """
    Confirm triple-riding violations across analyzed frames.

    A candidate begins when the configured minimum number of
    currently observed riders is associated with one motorcycle.
    """

    def __init__(
        self,
        *,
        minimum_riders: int,
        confirmation_frames: int,
        maximum_missed_frames: int,
    ) -> None:
        if minimum_riders < 2:
            raise ValueError("Minimum riders must be at least two.")

        if confirmation_frames <= 0:
            raise ValueError("Confirmation frames must be positive.")

        if maximum_missed_frames < 0:
            raise ValueError("Maximum missed frames cannot be negative.")

        self.minimum_riders = minimum_riders
        self.confirmation_frames = confirmation_frames
        self.maximum_missed_frames = maximum_missed_frames

        self._states: dict[
            int,
            _TripleRidingState,
        ] = {}

    def update(
        self,
        *,
        frame_number: int,
        timestamp_seconds: float,
        associations: TemporalRiderAssociationResult,
    ) -> TripleRidingDetectionResult:
        """Update violation states using one analyzed frame."""

        if frame_number <= 0:
            raise ValueError("Frame number must be positive.")

        if timestamp_seconds < 0:
            raise ValueError("Timestamp cannot be negative.")

        observed_by_motorcycle = self._group_observed_riders(associations)

        violating_motorcycles = {
            motorcycle_id: rider_associations
            for motorcycle_id, rider_associations in observed_by_motorcycle.items()
            if len(rider_associations) >= self.minimum_riders
        }

        transitions: list[TripleRidingTransition] = []

        updated_motorcycle_ids: set[int] = set()

        for motorcycle_id, rider_associations in violating_motorcycles.items():
            updated_motorcycle_ids.add(motorcycle_id)

            rider_ids = tuple(
                sorted(
                    association.person_track_id for association in rider_associations
                )
            )

            rider_count = len(rider_ids)

            average_score = (
                sum(association.smoothed_score for association in rider_associations)
                / rider_count
            )

            state = self._states.get(motorcycle_id)

            if state is None:
                state = _TripleRidingState(
                    motorcycle_track_id=(motorcycle_id),
                    rider_track_ids=rider_ids,
                    rider_count=rider_count,
                    peak_rider_count=rider_count,
                    average_association_score=(average_score),
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

                self._states[motorcycle_id] = state
            else:
                state.rider_track_ids = rider_ids
                state.rider_count = rider_count

                state.peak_rider_count = max(
                    state.peak_rider_count,
                    rider_count,
                )

                state.average_association_score = average_score

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
                        transition_type=(TripleRidingTransitionType.STARTED),
                        frame_number=frame_number,
                        timestamp_seconds=(timestamp_seconds),
                    )
                )

        for motorcycle_id, state in list(self._states.items()):
            if motorcycle_id in updated_motorcycle_ids:
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
                        transition_type=(TripleRidingTransitionType.ENDED),
                        frame_number=frame_number,
                        timestamp_seconds=(timestamp_seconds),
                    )
                )

            del self._states[motorcycle_id]

        public_states = tuple(
            state.to_public() for _, state in sorted(self._states.items())
        )

        return TripleRidingDetectionResult(
            states=public_states,
            transitions=tuple(transitions),
        )

    def reset(self) -> None:
        """Clear all state before another video."""

        self._states.clear()

    @staticmethod
    def _group_observed_riders(
        associations: TemporalRiderAssociationResult,
    ) -> dict[
        int,
        list[TemporalRiderAssociation],
    ]:
        """
        Group currently observed confirmed riders by motorcycle.

        Preserved but unobserved relationships do not create new
        confirmation evidence. The violation grace period handles
        temporary missing frames separately.
        """

        grouped: dict[
            int,
            list[TemporalRiderAssociation],
        ] = {}

        for association in associations.confirmed_associations:
            if not association.observed_this_frame:
                continue

            motorcycle_id = association.motorcycle_track_id

            grouped.setdefault(
                motorcycle_id,
                [],
            ).append(association)

        return grouped

    @staticmethod
    def _create_transition(
        *,
        state: _TripleRidingState,
        transition_type: TripleRidingTransitionType,
        frame_number: int,
        timestamp_seconds: float,
    ) -> TripleRidingTransition:
        confirmed_timestamp = state.confirmed_timestamp

        duration_seconds = 0.0

        if confirmed_timestamp is not None:
            duration_seconds = max(
                timestamp_seconds - confirmed_timestamp,
                0.0,
            )

        return TripleRidingTransition(
            transition_type=transition_type,
            motorcycle_track_id=(state.motorcycle_track_id),
            rider_track_ids=(state.rider_track_ids),
            rider_count=state.rider_count,
            peak_rider_count=(state.peak_rider_count),
            frame_number=frame_number,
            timestamp_seconds=timestamp_seconds,
            first_candidate_frame=(state.first_candidate_frame),
            confirmed_frame=(state.confirmed_frame),
            duration_seconds=duration_seconds,
        )
