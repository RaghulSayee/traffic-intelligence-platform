from app.detection.types import (
    BoundingBox,
    Detection,
)
from app.tracking.multi_object import (
    MultiObjectTracker,
)


def create_detection(
    *,
    x1: float,
    confidence: float = 0.90,
    class_id: int = 2,
    class_name: str = "car",
) -> Detection:
    return Detection(
        class_id=class_id,
        class_name=class_name,
        confidence=confidence,
        bounding_box=BoundingBox(
            x1=x1,
            y1=50,
            x2=x1 + 100,
            y2=150,
        ),
        model_name="test-model",
    )


def create_tracker(
    *,
    maximum_missed_frames: int = 2,
) -> MultiObjectTracker:
    return MultiObjectTracker(
        high_confidence_threshold=0.60,
        low_confidence_threshold=0.35,
        primary_iou_threshold=0.30,
        secondary_iou_threshold=0.15,
        minimum_confirmed_hits=2,
        maximum_missed_frames=(maximum_missed_frames),
        process_noise=1.0,
        measurement_noise=10.0,
    )


def test_same_object_keeps_track_id() -> None:
    tracker = create_tracker()

    first_result = tracker.update(
        detections=(
            create_detection(
                x1=10,
            ),
        ),
        timestamp_seconds=0.0,
    )

    first_track = first_result.tracks[0]

    assert first_track.track_id == 1
    assert first_track.confirmed is False

    second_result = tracker.update(
        detections=(
            create_detection(
                x1=15,
            ),
        ),
        timestamp_seconds=0.1,
    )

    second_track = second_result.tracks[0]

    assert second_track.track_id == 1
    assert second_track.confirmed is True
    assert second_track.hits == 2


def test_two_objects_receive_different_ids() -> None:
    tracker = create_tracker()

    result = tracker.update(
        detections=(
            create_detection(
                x1=10,
            ),
            create_detection(
                x1=300,
            ),
        ),
        timestamp_seconds=0.0,
    )

    assert {track.track_id for track in result.tracks} == {1, 2}


def test_low_confidence_detection_maintains_existing_track() -> None:
    tracker = create_tracker()

    first_result = tracker.update(
        detections=(
            create_detection(
                x1=10,
                confidence=0.90,
            ),
        ),
        timestamp_seconds=0.0,
    )

    original_track_id = first_result.tracks[0].track_id

    second_result = tracker.update(
        detections=(
            create_detection(
                x1=14,
                confidence=0.45,
            ),
        ),
        timestamp_seconds=0.1,
    )

    assert len(second_result.tracks) == 1

    assert second_result.tracks[0].track_id == original_track_id


def test_low_confidence_detection_does_not_create_track() -> None:
    tracker = create_tracker()

    result = tracker.update(
        detections=(
            create_detection(
                x1=10,
                confidence=0.45,
            ),
        ),
        timestamp_seconds=0.0,
    )

    assert result.tracks == ()
    assert result.active_track_count == 0


def test_track_is_removed_after_too_many_misses() -> None:
    tracker = create_tracker(maximum_missed_frames=1)

    first_result = tracker.update(
        detections=(
            create_detection(
                x1=10,
            ),
        ),
        timestamp_seconds=0.0,
    )

    track_id = first_result.tracks[0].track_id

    tracker.update(
        detections=(),
        timestamp_seconds=0.1,
    )

    final_result = tracker.update(
        detections=(),
        timestamp_seconds=0.2,
    )

    assert track_id in (final_result.removed_track_ids)

    assert final_result.active_track_count == 0
