from app.reasoning.rider_motorcycle import (
    RiderAssociationFeatures,
)
from app.reasoning.temporal_rider import (
    TemporalRiderAssociation,
    TemporalRiderAssociationResult,
)
from app.reasoning.triple_riding import (
    TripleRidingTransitionType,
    TripleRidingViolationDetector,
)


def create_features() -> RiderAssociationFeatures:
    return RiderAssociationFeatures(
        horizontal_overlap_score=0.90,
        anchor_distance_score=0.85,
        vertical_position_score=0.90,
        motion_similarity_score=0.80,
        containment_score=1.0,
    )


def create_temporal_result(
    *,
    riders_by_motorcycle: dict[
        int,
        tuple[int, ...],
    ],
    observed_this_frame: bool = True,
) -> TemporalRiderAssociationResult:
    associations = []

    for motorcycle_id, person_ids in riders_by_motorcycle.items():
        for person_id in person_ids:
            associations.append(
                TemporalRiderAssociation(
                    person_track_id=person_id,
                    motorcycle_track_id=(motorcycle_id),
                    latest_score=0.85,
                    smoothed_score=0.85,
                    consecutive_matches=4,
                    total_matches=4,
                    missed_frames=0,
                    confirmed=True,
                    observed_this_frame=(observed_this_frame),
                    features=create_features(),
                )
            )

    return TemporalRiderAssociationResult(
        associations=tuple(associations),
    )


def create_empty_result() -> TemporalRiderAssociationResult:
    return TemporalRiderAssociationResult(
        associations=(),
    )


def test_three_riders_require_confirmation_frames() -> None:
    detector = TripleRidingViolationDetector(
        minimum_riders=3,
        confirmation_frames=3,
        maximum_missed_frames=2,
    )

    frame_result = create_temporal_result(
        riders_by_motorcycle={
            10: (1, 2, 3),
        }
    )

    first = detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=frame_result,
    )

    second = detector.update(
        frame_number=6,
        timestamp_seconds=0.2,
        associations=frame_result,
    )

    third = detector.update(
        frame_number=11,
        timestamp_seconds=0.4,
        associations=frame_result,
    )

    assert first.active_violations == ()
    assert second.active_violations == ()

    assert len(third.active_violations) == 1

    assert len(third.transitions) == 1

    assert third.transitions[0].transition_type == TripleRidingTransitionType.STARTED


def test_two_riders_are_not_triple_riding() -> None:
    detector = TripleRidingViolationDetector(
        minimum_riders=3,
        confirmation_frames=1,
        maximum_missed_frames=1,
    )

    result = detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=create_temporal_result(
            riders_by_motorcycle={
                10: (1, 2),
            }
        ),
    )

    assert result.states == ()
    assert result.transitions == ()


def test_started_transition_is_emitted_only_once() -> None:
    detector = TripleRidingViolationDetector(
        minimum_riders=3,
        confirmation_frames=1,
        maximum_missed_frames=1,
    )

    frame_result = create_temporal_result(
        riders_by_motorcycle={
            10: (1, 2, 3),
        }
    )

    first = detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=frame_result,
    )

    second = detector.update(
        frame_number=6,
        timestamp_seconds=0.2,
        associations=frame_result,
    )

    assert len(first.transitions) == 1
    assert second.transitions == ()

    assert len(second.active_violations) == 1


def test_confirmed_violation_survives_short_gap() -> None:
    detector = TripleRidingViolationDetector(
        minimum_riders=3,
        confirmation_frames=1,
        maximum_missed_frames=1,
    )

    detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=create_temporal_result(
            riders_by_motorcycle={
                10: (1, 2, 3),
            }
        ),
    )

    missed = detector.update(
        frame_number=6,
        timestamp_seconds=0.2,
        associations=create_empty_result(),
    )

    assert len(missed.active_violations) == 1

    assert missed.active_violations[0].observed_this_frame is False


def test_violation_ends_after_missed_limit() -> None:
    detector = TripleRidingViolationDetector(
        minimum_riders=3,
        confirmation_frames=1,
        maximum_missed_frames=1,
    )

    detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=create_temporal_result(
            riders_by_motorcycle={
                10: (1, 2, 3),
            }
        ),
    )

    detector.update(
        frame_number=6,
        timestamp_seconds=0.2,
        associations=create_empty_result(),
    )

    ended = detector.update(
        frame_number=11,
        timestamp_seconds=0.4,
        associations=create_empty_result(),
    )

    assert ended.states == ()
    assert len(ended.transitions) == 1

    transition = ended.transitions[0]

    assert transition.transition_type == TripleRidingTransitionType.ENDED

    assert transition.motorcycle_track_id == 10
    assert transition.duration_seconds == 0.4


def test_multiple_motorcycles_are_independent() -> None:
    detector = TripleRidingViolationDetector(
        minimum_riders=3,
        confirmation_frames=1,
        maximum_missed_frames=1,
    )

    result = detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=create_temporal_result(
            riders_by_motorcycle={
                10: (1, 2, 3),
                20: (4, 5, 6),
            }
        ),
    )

    assert len(result.active_violations) == 2

    assert {
        violation.motorcycle_track_id for violation in result.active_violations
    } == {
        10,
        20,
    }


def test_unobserved_relationships_do_not_confirm_violation() -> None:
    detector = TripleRidingViolationDetector(
        minimum_riders=3,
        confirmation_frames=1,
        maximum_missed_frames=1,
    )

    result = detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=create_temporal_result(
            riders_by_motorcycle={
                10: (1, 2, 3),
            },
            observed_this_frame=False,
        ),
    )

    assert result.states == ()
    assert result.transitions == ()
