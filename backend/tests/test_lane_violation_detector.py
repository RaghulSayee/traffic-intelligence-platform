import pytest

from app.detection.types import BoundingBox
from app.reasoning.lane_occupancy import (
    LaneOccupancyAnalyzer,
)
from app.reasoning.lane_violation import (
    LaneViolationDetector,
    LaneViolationTransitionType,
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
        enabled_violations=(["lane_violation"] if enabled else []),
        monitoring_zone={
            "points": [
                {
                    "x": 0.05,
                    "y": 0.05,
                },
                {
                    "x": 0.95,
                    "y": 0.05,
                },
                {
                    "x": 0.95,
                    "y": 0.95,
                },
                {
                    "x": 0.05,
                    "y": 0.95,
                },
            ]
        },
        lanes=[
            {
                "lane_id": "lane-1",
                "polygon": {
                    "points": [
                        {
                            "x": 0.10,
                            "y": 0.10,
                        },
                        {
                            "x": 0.60,
                            "y": 0.10,
                        },
                        {
                            "x": 0.60,
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
    x1: float = 450.0,
    x2: float = 550.0,
    velocity_x: float = 80.0,
    confirmed: bool = True,
) -> TrackedObject:
    return TrackedObject(
        track_id=1,
        class_id=2,
        class_name="car",
        confidence=0.95,
        bounding_box=BoundingBox(
            x1=x1,
            y1=100.0,
            x2=x2,
            y2=220.0,
        ),
        age=5,
        hits=5,
        missed_frames=0,
        confirmed=confirmed,
        velocity_x=velocity_x,
        velocity_y=0.0,
    )


def create_detector(
    *,
    confirmation_frames: int = 2,
    maximum_missed_frames: int = 1,
) -> LaneViolationDetector:
    occupancy_analyzer = LaneOccupancyAnalyzer(
        minimum_speed_pixels_per_second=(15.0),
        boundary_tolerance_pixels=12.0,
    )

    return LaneViolationDetector(
        occupancy_analyzer=(occupancy_analyzer),
        confirmation_frames=(confirmation_frames),
        maximum_missed_frames=(maximum_missed_frames),
    )


def update(
    detector: LaneViolationDetector,
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


def test_confirms_after_required_candidate_frames() -> None:
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

    assert second.states[0].nearest_lane_id == "lane-1"

    assert len(second.transitions) == 1

    transition = second.transitions[0]

    assert transition.transition_type == LaneViolationTransitionType.STARTED

    assert transition.track_id == 1
    assert transition.confirmed_frame == 2
    assert transition.duration_seconds == 0.0


def test_vehicle_inside_lane_does_not_create_state() -> None:
    detector = create_detector()

    result = update(
        detector,
        frame_number=1,
        tracks=(
            create_track(
                x1=220.0,
                x2=320.0,
            ),
        ),
    )

    assert len(result.occupancy.observations) == 1

    assert result.occupancy.observations[0].violation_candidate is False

    assert result.states == ()
    assert result.transitions == ()


def test_unconfirmed_candidate_survives_no_gap() -> None:
    detector = create_detector(
        confirmation_frames=3,
    )

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

    assert first.states[0].confirmed is False

    assert second.states[0].consecutive_violation_frames == 2

    assert second.transitions == ()


def test_unconfirmed_streak_restarts_after_gap() -> None:
    detector = create_detector(
        confirmation_frames=2,
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
        tracks=(
            create_track(
                x1=220.0,
                x2=320.0,
            ),
        ),
    )

    returned = update(
        detector,
        frame_number=3,
        tracks=(create_track(),),
    )

    assert gap.states[0].missed_frames == 1

    assert returned.states[0].confirmed is False

    assert returned.states[0].first_candidate_frame == 3

    assert returned.states[0].consecutive_violation_frames == 1


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

    started = update(
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

    assert started.transitions[0].transition_type == LaneViolationTransitionType.STARTED

    assert ended.states == ()
    assert len(ended.transitions) == 1

    transition = ended.transitions[0]

    assert transition.transition_type == LaneViolationTransitionType.ENDED

    assert transition.track_id == 1

    assert transition.duration_seconds == (pytest.approx(0.2))


def test_disabled_rule_creates_no_state() -> None:
    detector = create_detector()

    result = update(
        detector,
        frame_number=1,
        tracks=(create_track(),),
        scene=create_scene(enabled=False),
    )

    assert result.occupancy.observations == ()

    assert result.states == ()
    assert result.transitions == ()


def test_reset_removes_existing_state() -> None:
    detector = create_detector(
        confirmation_frames=1,
    )

    update(
        detector,
        frame_number=1,
        tracks=(create_track(),),
    )

    detector.reset()

    result = update(
        detector,
        frame_number=2,
        tracks=(),
    )

    assert result.states == ()
    assert result.transitions == ()
