import pytest

from app.detection.types import BoundingBox
from app.reasoning.wrong_way import (
    WrongWayTransitionType,
    WrongWayViolationDetector,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)
from app.tracking.types import TrackedObject


def create_scene(
    *,
    enabled: bool = True,
) -> CameraSceneConfiguration:
    return CameraSceneConfiguration(
        enabled_violations=(["wrong_way"] if enabled else []),
        lanes=[
            {
                "lane_id": "northbound",
                "polygon": {
                    "points": [
                        {
                            "x": 0.10,
                            "y": 0.10,
                        },
                        {
                            "x": 0.90,
                            "y": 0.10,
                        },
                        {
                            "x": 0.90,
                            "y": 0.90,
                        },
                        {
                            "x": 0.10,
                            "y": 0.90,
                        },
                    ]
                },
                "allowed_direction": {
                    "x": 0.0,
                    "y": -1.0,
                },
            }
        ],
    )


def create_track(
    *,
    velocity_x: float = 0.0,
    velocity_y: float = 80.0,
    x1: float = 200.0,
) -> TrackedObject:
    return TrackedObject(
        track_id=1,
        class_id=2,
        class_name="car",
        confidence=0.95,
        bounding_box=BoundingBox(
            x1=x1,
            y1=100,
            x2=x1 + 100,
            y2=220,
        ),
        age=5,
        hits=5,
        missed_frames=0,
        confirmed=True,
        velocity_x=velocity_x,
        velocity_y=velocity_y,
    )


def create_detector(
    *,
    confirmation_frames: int = 2,
    maximum_missed_frames: int = 1,
) -> WrongWayViolationDetector:
    return WrongWayViolationDetector(
        minimum_speed_pixels_per_second=20.0,
        opposite_cosine_threshold=-0.50,
        confirmation_frames=confirmation_frames,
        maximum_missed_frames=(maximum_missed_frames),
    )


def update(
    detector: WrongWayViolationDetector,
    *,
    frame_number: int,
    tracks: tuple[TrackedObject, ...],
    scene: CameraSceneConfiguration | None = None,
):
    return detector.update(
        frame_number=frame_number,
        timestamp_seconds=((frame_number - 1) * 0.1),
        tracks=tracks,
        scene=(scene if scene is not None else create_scene()),
        image_width=640,
        image_height=360,
    )


def test_confirms_opposite_direction_after_required_frames() -> None:
    detector = create_detector()

    first = update(
        detector,
        frame_number=1,
        tracks=(create_track(),),
    )

    second = update(
        detector,
        frame_number=2,
        tracks=(create_track(),),
    )

    assert len(first.states) == 1
    assert first.states[0].confirmed is False

    assert len(second.states) == 1
    assert second.states[0].confirmed is True

    assert second.states[0].lane_id == "northbound"

    assert second.states[0].cosine_similarity == (pytest.approx(-1.0))

    assert len(second.transitions) == 1

    assert second.transitions[0].transition_type == WrongWayTransitionType.STARTED


def test_compliant_direction_does_not_create_candidate() -> None:
    detector = create_detector()

    result = update(
        detector,
        frame_number=1,
        tracks=(
            create_track(
                velocity_y=-80.0,
            ),
        ),
    )

    assert result.states == ()
    assert result.transitions == ()


def test_slow_vehicle_is_ignored() -> None:
    detector = create_detector()

    result = update(
        detector,
        frame_number=1,
        tracks=(
            create_track(
                velocity_y=10.0,
            ),
        ),
    )

    assert result.states == ()


def test_vehicle_outside_lane_is_ignored() -> None:
    detector = create_detector()

    result = update(
        detector,
        frame_number=1,
        tracks=(
            create_track(
                x1=590.0,
            ),
        ),
    )

    assert result.states == ()


def test_disabled_rule_does_not_create_candidate() -> None:
    detector = create_detector()

    result = update(
        detector,
        frame_number=1,
        tracks=(create_track(),),
        scene=create_scene(enabled=False),
    )

    assert result.states == ()


def test_confirmed_violation_survives_short_gap() -> None:
    detector = create_detector(
        confirmation_frames=1,
        maximum_missed_frames=1,
    )

    update(
        detector,
        frame_number=1,
        tracks=(create_track(),),
    )

    gap = update(
        detector,
        frame_number=2,
        tracks=(),
    )

    assert len(gap.states) == 1
    assert gap.states[0].confirmed is True
    assert gap.states[0].missed_frames == 1
    assert gap.transitions == ()


def test_confirmed_violation_emits_ended_transition() -> None:
    detector = create_detector(
        confirmation_frames=1,
        maximum_missed_frames=1,
    )

    update(
        detector,
        frame_number=1,
        tracks=(create_track(),),
    )

    update(
        detector,
        frame_number=2,
        tracks=(),
    )

    ended = update(
        detector,
        frame_number=3,
        tracks=(),
    )

    assert ended.states == ()
    assert len(ended.transitions) == 1

    transition = ended.transitions[0]

    assert transition.transition_type == WrongWayTransitionType.ENDED

    assert transition.track_id == 1
    assert transition.lane_id == "northbound"

    assert transition.duration_seconds == (pytest.approx(0.2))
