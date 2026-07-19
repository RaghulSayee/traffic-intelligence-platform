from dataclasses import dataclass

from app.reasoning.rider_motorcycle import (
    RiderAssociationFeatures,
    RiderAssociationResult,
)


AssociationKey = tuple[int, int]


@dataclass(frozen=True, slots=True)
class TemporalRiderAssociation:
    """A rider relationship maintained across analyzed frames."""

    person_track_id: int
    motorcycle_track_id: int

    latest_score: float
    smoothed_score: float

    consecutive_matches: int
    total_matches: int
    missed_frames: int

    confirmed: bool
    observed_this_frame: bool

    features: RiderAssociationFeatures


@dataclass(frozen=True, slots=True)
class TemporalRiderAssociationResult:
    """Temporal rider relationships after processing one frame."""

    associations: tuple[TemporalRiderAssociation, ...]

    removed_pairs: tuple[AssociationKey, ...] = ()

    @property
    def confirmed_associations(
        self,
    ) -> tuple[TemporalRiderAssociation, ...]:
        """Return relationships that passed temporal confirmation."""

        return tuple(
            association for association in self.associations if association.confirmed
        )

    def rider_counts_by_motorcycle(
        self,
    ) -> dict[int, int]:
        """Count confirmed riders for each motorcycle."""

        counts: dict[int, int] = {}

        for association in self.confirmed_associations:
            motorcycle_id = association.motorcycle_track_id

            counts[motorcycle_id] = counts.get(motorcycle_id, 0) + 1

        return counts


@dataclass(slots=True)
class _TemporalState:
    """Mutable internal relationship state."""

    person_track_id: int
    motorcycle_track_id: int

    latest_score: float
    smoothed_score: float

    consecutive_matches: int
    total_matches: int
    missed_frames: int

    confirmed: bool
    observed_this_frame: bool

    features: RiderAssociationFeatures

    def to_public(
        self,
    ) -> TemporalRiderAssociation:
        """Create an immutable public result."""

        return TemporalRiderAssociation(
            person_track_id=self.person_track_id,
            motorcycle_track_id=(self.motorcycle_track_id),
            latest_score=self.latest_score,
            smoothed_score=self.smoothed_score,
            consecutive_matches=(self.consecutive_matches),
            total_matches=self.total_matches,
            missed_frames=self.missed_frames,
            confirmed=self.confirmed,
            observed_this_frame=(self.observed_this_frame),
            features=self.features,
        )


class TemporalRiderAssociationSmoother:
    """
    Confirm and preserve rider relationships across frames.

    A relationship becomes confirmed only after it appears for the
    configured number of consecutive analyzed frames.

    Confirmed relationships survive short detection gaps.
    """

    def __init__(
        self,
        *,
        confirmation_frames: int,
        maximum_missed_frames: int,
        score_alpha: float,
    ) -> None:
        if confirmation_frames <= 0:
            raise ValueError("Confirmation frames must be positive.")

        if maximum_missed_frames < 0:
            raise ValueError("Maximum missed frames cannot be negative.")

        if not 0.0 < score_alpha <= 1.0:
            raise ValueError(
                "Score alpha must be greater than zero and no greater than one."
            )

        self.confirmation_frames = confirmation_frames

        self.maximum_missed_frames = maximum_missed_frames

        self.score_alpha = score_alpha

        self._states: dict[
            AssociationKey,
            _TemporalState,
        ] = {}

    def update(
        self,
        frame_result: RiderAssociationResult,
    ) -> TemporalRiderAssociationResult:
        """Update temporal state using one analyzed frame."""

        observed_associations = {
            (
                association.person_track_id,
                association.motorcycle_track_id,
            ): association
            for association in frame_result.associations
        }

        for state in self._states.values():
            state.observed_this_frame = False

        newly_confirmed_keys: list[AssociationKey] = []

        for key, association in observed_associations.items():
            state = self._states.get(key)

            if state is None:
                confirmed = self.confirmation_frames <= 1

                state = _TemporalState(
                    person_track_id=(association.person_track_id),
                    motorcycle_track_id=(association.motorcycle_track_id),
                    latest_score=association.score,
                    smoothed_score=association.score,
                    consecutive_matches=1,
                    total_matches=1,
                    missed_frames=0,
                    confirmed=confirmed,
                    observed_this_frame=True,
                    features=association.features,
                )

                self._states[key] = state

                if confirmed:
                    newly_confirmed_keys.append(key)

                continue

            previously_confirmed = state.confirmed

            state.latest_score = association.score

            state.smoothed_score = (
                self.score_alpha * association.score
                + (1.0 - self.score_alpha) * state.smoothed_score
            )

            state.consecutive_matches += 1
            state.total_matches += 1
            state.missed_frames = 0
            state.observed_this_frame = True
            state.features = association.features

            if (
                not state.confirmed
                and state.consecutive_matches >= self.confirmation_frames
            ):
                state.confirmed = True

            if state.confirmed and not previously_confirmed:
                newly_confirmed_keys.append(key)

        removed_pairs: list[AssociationKey] = []

        for key, state in list(self._states.items()):
            if key in observed_associations:
                continue

            state.missed_frames += 1
            state.consecutive_matches = 0
            state.observed_this_frame = False

            if state.missed_frames > self.maximum_missed_frames:
                removed_pairs.append(key)
                del self._states[key]

        # When a new relationship for a person is confirmed,
        # remove that person's older motorcycle relationships.
        for confirmed_key in newly_confirmed_keys:
            if confirmed_key not in self._states:
                continue

            person_track_id, _ = confirmed_key

            for other_key in list(self._states):
                other_person_id, _ = other_key

                if other_person_id == person_track_id and other_key != confirmed_key:
                    removed_pairs.append(other_key)

                    del self._states[other_key]

        public_associations = tuple(
            state.to_public() for _, state in sorted(self._states.items())
        )

        return TemporalRiderAssociationResult(
            associations=public_associations,
            removed_pairs=tuple(sorted(set(removed_pairs))),
        )

    def reset(self) -> None:
        """Clear relationships before processing another video."""

        self._states.clear()
