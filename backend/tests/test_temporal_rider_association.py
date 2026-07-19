import pytest

from app.reasoning.rider_motorcycle import (
    RiderAssociationFeatures,
    RiderAssociationResult,
    RiderMotorcycleAssociation,
)
from app.reasoning.temporal_rider import (
    TemporalRiderAssociationSmoother,
)


def create_features() -> RiderAssociationFeatures:
    return RiderAssociationFeatures(
        horizontal_overlap_score=0.80,
        anchor_distance_score=0.80,
        vertical_position_score=0.80,
        motion_similarity_score=0.80,
        containment_score=1.0,
    )


def create_frame_result(
    *,
    person_track_id: int = 1,
    motorcycle_track_id: int = 10,
    score: float = 0.80,
) -> RiderAssociationResult:
    return RiderAssociationResult(
        associations=(
            RiderMotorcycleAssociation(
                person_track_id=person_track_id,
                motorcycle_track_id=(motorcycle_track_id),
                score=score,
                features=create_features(),
            ),
        ),
        unassigned_person_track_ids=(),
    )


def create_empty_result() -> RiderAssociationResult:
    return RiderAssociationResult(
        associations=(),
        unassigned_person_track_ids=(),
    )


def test_relationship_requires_consecutive_confirmation() -> None:
    smoother = TemporalRiderAssociationSmoother(
        confirmation_frames=3,
        maximum_missed_frames=2,
        score_alpha=0.40,
    )

    first = smoother.update(create_frame_result())

    second = smoother.update(create_frame_result())

    third = smoother.update(create_frame_result())

    assert first.confirmed_associations == ()
    assert second.confirmed_associations == ()

    assert len(third.confirmed_associations) == 1

    association = third.confirmed_associations[0]

    assert association.confirmed is True
    assert association.consecutive_matches == 3
    assert association.total_matches == 3


def test_confirmed_relationship_survives_short_gap() -> None:
    smoother = TemporalRiderAssociationSmoother(
        confirmation_frames=2,
        maximum_missed_frames=2,
        score_alpha=0.40,
    )

    smoother.update(create_frame_result())

    confirmed = smoother.update(create_frame_result())

    assert len(confirmed.confirmed_associations) == 1

    missed = smoother.update(create_empty_result())

    assert len(missed.confirmed_associations) == 1

    association = missed.confirmed_associations[0]

    assert association.missed_frames == 1
    assert association.observed_this_frame is False


def test_relationship_expires_after_missed_limit() -> None:
    smoother = TemporalRiderAssociationSmoother(
        confirmation_frames=1,
        maximum_missed_frames=1,
        score_alpha=0.40,
    )

    smoother.update(create_frame_result())

    first_miss = smoother.update(create_empty_result())

    assert len(first_miss.confirmed_associations) == 1

    second_miss = smoother.update(create_empty_result())

    assert second_miss.associations == ()

    assert second_miss.removed_pairs == ((1, 10),)


def test_one_frame_noise_never_becomes_confirmed() -> None:
    smoother = TemporalRiderAssociationSmoother(
        confirmation_frames=2,
        maximum_missed_frames=1,
        score_alpha=0.40,
    )

    first = smoother.update(create_frame_result())

    assert first.confirmed_associations == ()

    smoother.update(create_empty_result())

    final = smoother.update(create_empty_result())

    assert final.associations == ()


def test_new_confirmed_motorcycle_replaces_old_one() -> None:
    smoother = TemporalRiderAssociationSmoother(
        confirmation_frames=2,
        maximum_missed_frames=3,
        score_alpha=0.40,
    )

    smoother.update(create_frame_result(motorcycle_track_id=10))

    old_confirmed = smoother.update(create_frame_result(motorcycle_track_id=10))

    assert old_confirmed.confirmed_associations[0].motorcycle_track_id == 10

    first_new_frame = smoother.update(create_frame_result(motorcycle_track_id=20))

    # The new relationship is not confirmed yet,
    # so the old confirmed relationship remains active.
    assert first_new_frame.confirmed_associations[0].motorcycle_track_id == 10

    second_new_frame = smoother.update(create_frame_result(motorcycle_track_id=20))

    assert len(second_new_frame.confirmed_associations) == 1

    assert second_new_frame.confirmed_associations[0].motorcycle_track_id == 20

    assert (1, 10) in (second_new_frame.removed_pairs)


def test_score_uses_exponential_smoothing() -> None:
    smoother = TemporalRiderAssociationSmoother(
        confirmation_frames=2,
        maximum_missed_frames=1,
        score_alpha=0.50,
    )

    smoother.update(create_frame_result(score=1.0))

    result = smoother.update(create_frame_result(score=0.0))

    association = result.associations[0]

    assert association.latest_score == 0.0

    assert association.smoothed_score == pytest.approx(0.50)
