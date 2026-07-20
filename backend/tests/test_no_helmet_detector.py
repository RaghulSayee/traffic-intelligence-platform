from app.detection.types import BoundingBox
from app.reasoning.helmet_rider import (
    HelmetRiderAssociation,
    HelmetRiderAssociationResult,
)
from app.reasoning.no_helmet import (
    NoHelmetTransitionType,
    NoHelmetViolationDetector,
)


def create_result(
    *,
    class_name: str = "no_helmet",
) -> HelmetRiderAssociationResult:
    box = BoundingBox(
        x1=100,
        y1=40,
        x2=150,
        y2=100,
    )

    return HelmetRiderAssociationResult(
        associations=(
            HelmetRiderAssociation(
                person_track_id=1,
                motorcycle_track_id=10,
                class_name=class_name,
                detection_confidence=0.90,
                association_score=0.85,
                head_region=box,
                detection_box=box,
            ),
        )
    )


def empty_result() -> HelmetRiderAssociationResult:
    return HelmetRiderAssociationResult(associations=())


def test_confirms_no_helmet_after_required_frames() -> None:
    detector = NoHelmetViolationDetector(
        confirmation_frames=2,
        maximum_missed_frames=1,
        confidence_alpha=0.40,
    )

    first = detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=create_result(),
    )

    second = detector.update(
        frame_number=2,
        timestamp_seconds=0.1,
        associations=create_result(),
    )

    assert len(first.states) == 1
    assert first.states[0].confirmed is False

    assert len(second.states) == 1
    assert second.states[0].confirmed is True

    assert len(second.transitions) == 1

    assert second.transitions[0].transition_type == NoHelmetTransitionType.STARTED


def test_confirmed_violation_survives_short_gap() -> None:
    detector = NoHelmetViolationDetector(
        confirmation_frames=1,
        maximum_missed_frames=1,
        confidence_alpha=0.40,
    )

    detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=create_result(),
    )

    result = detector.update(
        frame_number=2,
        timestamp_seconds=0.1,
        associations=empty_result(),
    )

    assert len(result.states) == 1
    assert result.states[0].confirmed is True
    assert result.states[0].missed_frames == 1
    assert result.transitions == ()


def test_confirmed_violation_emits_ended_transition() -> None:
    detector = NoHelmetViolationDetector(
        confirmation_frames=1,
        maximum_missed_frames=1,
        confidence_alpha=0.40,
    )

    detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=create_result(),
    )

    detector.update(
        frame_number=2,
        timestamp_seconds=0.1,
        associations=empty_result(),
    )

    ended = detector.update(
        frame_number=3,
        timestamp_seconds=0.2,
        associations=empty_result(),
    )

    assert ended.states == ()
    assert len(ended.transitions) == 1

    transition = ended.transitions[0]

    assert transition.transition_type == NoHelmetTransitionType.ENDED

    assert transition.person_track_id == 1
    assert transition.motorcycle_track_id == 10
    assert transition.duration_seconds == 0.2


def test_helmet_label_does_not_create_violation() -> None:
    detector = NoHelmetViolationDetector(
        confirmation_frames=1,
        maximum_missed_frames=1,
        confidence_alpha=0.40,
    )

    result = detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        associations=create_result(class_name="helmet"),
    )

    assert result.states == ()
    assert result.transitions == ()
