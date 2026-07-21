import pytest

from app.detection.types import BoundingBox
from app.reasoning.red_light import (
    RedLightCrossingDetector,
    RedLightTransitionType,
)
from app.reasoning.traffic_light_state import (
    TrafficLightState,
)
from app.reasoning.traffic_light_temporal import (
    StableTrafficLightSnapshot,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)
from app.tracking.types import TrackedObject


IMAGE_WIDTH = 101
IMAGE_HEIGHT = 101


def create_scene(
    *,
    enabled: bool = True,
    linked_stop_line: bool = True,
) -> CameraSceneConfiguration:
    stop_line = {
        "stop_line_id": "stop-1",
        "line": {
            "start": {
                "x": 0.20,
                "y": 0.50,
            },
            "end": {
                "x": 0.80,
                "y": 0.50,
            },
        },
    }

    if linked_stop_line:
        stop_line.update(
            {
                "lane_id": "lane-1",
                "traffic_light_region_id": ("signal-1"),
            }
        )

    return CameraSceneConfiguration(
        enabled_violations=(["red_light"] if enabled else []),
        lanes=[
            {
                "lane_id": "lane-1",
                "name": "Southbound Lane",
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
                    "y": 1.0,
                },
            }
        ],
        traffic_light_regions=[
            {
                "region_id": "signal-1",
                "name": "Main Signal",
                "polygon": {
                    "points": [
                        {
                            "x": 0.05,
                            "y": 0.05,
                        },
                        {
                            "x": 0.15,
                            "y": 0.05,
                        },
                        {
                            "x": 0.15,
                            "y": 0.20,
                        },
                        {
                            "x": 0.05,
                            "y": 0.20,
                        },
                    ]
                },
            }
        ],
        stop_lines=[stop_line],
    )


def create_signal_state(
    state: TrafficLightState,
    *,
    confidence: float = 0.95,
    raw_state: TrafficLightState | None = None,
) -> StableTrafficLightSnapshot:
    return StableTrafficLightSnapshot(
        region_id="signal-1",
        region_name="Main Signal",
        raw_state=(raw_state if raw_state is not None else state),
        raw_confidence=confidence,
        stable_state=state,
        stable_confidence=confidence,
        candidate_state=(TrafficLightState.UNKNOWN),
        candidate_confidence=0.0,
        consecutive_candidate_frames=0,
        unknown_frames=0,
        red_score=(0.20 if state == TrafficLightState.RED else 0.0),
        yellow_score=(0.20 if state == TrafficLightState.YELLOW else 0.0),
        green_score=(0.20 if state == TrafficLightState.GREEN else 0.0),
        active_pixel_ratio=0.20,
        last_observed_frame=1,
        observed_this_frame=True,
    )


def create_track(
    *,
    anchor_x: float = 50.0,
    anchor_y: float,
    velocity_x: float = 0.0,
    velocity_y: float = 100.0,
    confirmed: bool = True,
    missed_frames: int = 0,
) -> TrackedObject:
    box_height = 20.0
    box_width = 20.0

    y1 = anchor_y - box_height * 0.90

    return TrackedObject(
        track_id=1,
        class_id=2,
        class_name="car",
        confidence=0.90,
        bounding_box=BoundingBox(
            x1=anchor_x - box_width / 2.0,
            y1=y1,
            x2=anchor_x + box_width / 2.0,
            y2=y1 + box_height,
        ),
        age=5,
        hits=5,
        missed_frames=missed_frames,
        confirmed=confirmed,
        velocity_x=velocity_x,
        velocity_y=velocity_y,
    )


def create_detector(
    *,
    minimum_speed: float = 10.0,
    minimum_direction_cosine: float = 0.25,
    minimum_signal_confidence: float = 0.60,
) -> RedLightCrossingDetector:
    return RedLightCrossingDetector(
        minimum_speed_pixels_per_second=(minimum_speed),
        minimum_direction_cosine=(minimum_direction_cosine),
        line_crossing_tolerance_pixels=3.0,
        minimum_signal_confidence=(minimum_signal_confidence),
        maximum_missed_frames=2,
    )


def update(
    detector: RedLightCrossingDetector,
    *,
    frame_number: int,
    track: TrackedObject,
    signal_state: TrafficLightState,
    signal_confidence: float = 0.95,
    scene: CameraSceneConfiguration | None = None,
):
    return detector.update(
        frame_number=frame_number,
        timestamp_seconds=((frame_number - 1) * 0.10),
        tracks=(track,),
        traffic_light_states=(
            create_signal_state(
                signal_state,
                confidence=(signal_confidence),
            ),
        ),
        scene=(scene if scene is not None else create_scene()),
        image_width=IMAGE_WIDTH,
        image_height=IMAGE_HEIGHT,
    )


def test_detects_stop_line_crossing_on_red() -> None:
    detector = create_detector()

    first = update(
        detector,
        frame_number=1,
        track=create_track(anchor_y=40.0),
        signal_state=TrafficLightState.RED,
    )

    crossed = update(
        detector,
        frame_number=2,
        track=create_track(anchor_y=60.0),
        signal_state=TrafficLightState.RED,
    )

    assert first.observations == ()
    assert first.transitions == ()

    assert len(crossed.observations) == 1
    assert len(crossed.transitions) == 1

    observation = crossed.observations[0]
    transition = crossed.transitions[0]

    assert observation.is_violation is True

    assert observation.signal_state == TrafficLightState.RED

    assert observation.previous_signed_distance_pixels < 0.0

    assert observation.signed_distance_pixels > 0.0

    assert transition.transition_type == RedLightTransitionType.STARTED

    assert transition.track_id == 1
    assert transition.stop_line_id == "stop-1"
    assert transition.lane_id == "lane-1"

    assert transition.traffic_light_region_id == "signal-1"


def test_green_crossing_is_not_a_violation() -> None:
    detector = create_detector()

    update(
        detector,
        frame_number=1,
        track=create_track(anchor_y=40.0),
        signal_state=(TrafficLightState.GREEN),
    )

    crossed = update(
        detector,
        frame_number=2,
        track=create_track(anchor_y=60.0),
        signal_state=(TrafficLightState.GREEN),
    )

    assert len(crossed.observations) == 1

    assert crossed.observations[0].is_violation is False

    assert crossed.transitions == ()


def test_uses_stable_state_not_raw_state() -> None:
    detector = create_detector()

    stable_green_raw_red = create_signal_state(
        TrafficLightState.GREEN,
        raw_state=(TrafficLightState.RED),
    )

    detector.update(
        frame_number=1,
        timestamp_seconds=0.0,
        tracks=(create_track(anchor_y=40.0),),
        traffic_light_states=(stable_green_raw_red,),
        scene=create_scene(),
        image_width=IMAGE_WIDTH,
        image_height=IMAGE_HEIGHT,
    )

    crossed = detector.update(
        frame_number=2,
        timestamp_seconds=0.1,
        tracks=(create_track(anchor_y=60.0),),
        traffic_light_states=(stable_green_raw_red,),
        scene=create_scene(),
        image_width=IMAGE_WIDTH,
        image_height=IMAGE_HEIGHT,
    )

    assert len(crossed.observations) == 1
    assert crossed.transitions == ()


def test_low_signal_confidence_is_not_a_violation() -> None:
    detector = create_detector(minimum_signal_confidence=0.60)

    update(
        detector,
        frame_number=1,
        track=create_track(anchor_y=40.0),
        signal_state=TrafficLightState.RED,
        signal_confidence=0.40,
    )

    crossed = update(
        detector,
        frame_number=2,
        track=create_track(anchor_y=60.0),
        signal_state=TrafficLightState.RED,
        signal_confidence=0.40,
    )

    assert len(crossed.observations) == 1
    assert crossed.transitions == ()


def test_crossing_outside_stop_line_segment_is_ignored() -> None:
    detector = create_detector()

    update(
        detector,
        frame_number=1,
        track=create_track(
            anchor_x=95.0,
            anchor_y=40.0,
        ),
        signal_state=TrafficLightState.RED,
    )

    crossed = update(
        detector,
        frame_number=2,
        track=create_track(
            anchor_x=95.0,
            anchor_y=60.0,
        ),
        signal_state=TrafficLightState.RED,
    )

    assert crossed.observations == ()
    assert crossed.transitions == ()


def test_reverse_direction_crossing_is_ignored() -> None:
    detector = create_detector()

    update(
        detector,
        frame_number=1,
        track=create_track(
            anchor_y=60.0,
            velocity_y=-100.0,
        ),
        signal_state=TrafficLightState.RED,
    )

    crossed = update(
        detector,
        frame_number=2,
        track=create_track(
            anchor_y=40.0,
            velocity_y=-100.0,
        ),
        signal_state=TrafficLightState.RED,
    )

    assert crossed.observations == ()
    assert crossed.transitions == ()


def test_slow_crossing_is_ignored() -> None:
    detector = create_detector(minimum_speed=10.0)

    update(
        detector,
        frame_number=1,
        track=create_track(
            anchor_y=40.0,
            velocity_y=5.0,
        ),
        signal_state=TrafficLightState.RED,
    )

    crossed = update(
        detector,
        frame_number=2,
        track=create_track(
            anchor_y=60.0,
            velocity_y=5.0,
        ),
        signal_state=TrafficLightState.RED,
    )

    assert crossed.observations == ()
    assert crossed.transitions == ()


def test_same_track_and_line_emits_only_once() -> None:
    detector = create_detector()

    update(
        detector,
        frame_number=1,
        track=create_track(anchor_y=40.0),
        signal_state=TrafficLightState.RED,
    )

    first_crossing = update(
        detector,
        frame_number=2,
        track=create_track(anchor_y=60.0),
        signal_state=TrafficLightState.RED,
    )

    update(
        detector,
        frame_number=3,
        track=create_track(
            anchor_y=40.0,
            velocity_y=-100.0,
        ),
        signal_state=TrafficLightState.RED,
    )

    second_crossing = update(
        detector,
        frame_number=4,
        track=create_track(anchor_y=60.0),
        signal_state=TrafficLightState.RED,
    )

    assert len(first_crossing.transitions) == 1
    assert second_crossing.transitions == ()

    assert len(second_crossing.observations) == 1

    assert second_crossing.observations[0].is_violation is False


def test_unlinked_stop_line_is_ignored() -> None:
    detector = create_detector()
    scene = create_scene(linked_stop_line=False)

    update(
        detector,
        frame_number=1,
        track=create_track(anchor_y=40.0),
        signal_state=TrafficLightState.RED,
        scene=scene,
    )

    crossed = update(
        detector,
        frame_number=2,
        track=create_track(anchor_y=60.0),
        signal_state=TrafficLightState.RED,
        scene=scene,
    )

    assert crossed.observations == ()
    assert crossed.transitions == ()


def test_disabled_rule_returns_empty_result() -> None:
    detector = create_detector()

    result = update(
        detector,
        frame_number=1,
        track=create_track(anchor_y=40.0),
        signal_state=TrafficLightState.RED,
        scene=create_scene(enabled=False),
    )

    assert result.observations == ()
    assert result.transitions == ()


def test_reset_allows_new_crossing() -> None:
    detector = create_detector()

    update(
        detector,
        frame_number=1,
        track=create_track(anchor_y=40.0),
        signal_state=TrafficLightState.RED,
    )

    first = update(
        detector,
        frame_number=2,
        track=create_track(anchor_y=60.0),
        signal_state=TrafficLightState.RED,
    )

    detector.reset()

    update(
        detector,
        frame_number=3,
        track=create_track(anchor_y=40.0),
        signal_state=TrafficLightState.RED,
    )

    second = update(
        detector,
        frame_number=4,
        track=create_track(anchor_y=60.0),
        signal_state=TrafficLightState.RED,
    )

    assert len(first.transitions) == 1
    assert len(second.transitions) == 1


@pytest.mark.parametrize(
    "keyword_arguments",
    [
        {
            "minimum_speed_pixels_per_second": -1.0,
            "minimum_direction_cosine": 0.25,
            "line_crossing_tolerance_pixels": 3.0,
            "minimum_signal_confidence": 0.60,
            "maximum_missed_frames": 2,
        },
        {
            "minimum_speed_pixels_per_second": 10.0,
            "minimum_direction_cosine": 1.1,
            "line_crossing_tolerance_pixels": 3.0,
            "minimum_signal_confidence": 0.60,
            "maximum_missed_frames": 2,
        },
        {
            "minimum_speed_pixels_per_second": 10.0,
            "minimum_direction_cosine": 0.25,
            "line_crossing_tolerance_pixels": 0.0,
            "minimum_signal_confidence": 0.60,
            "maximum_missed_frames": 2,
        },
        {
            "minimum_speed_pixels_per_second": 10.0,
            "minimum_direction_cosine": 0.25,
            "line_crossing_tolerance_pixels": 3.0,
            "minimum_signal_confidence": 1.1,
            "maximum_missed_frames": 2,
        },
        {
            "minimum_speed_pixels_per_second": 10.0,
            "minimum_direction_cosine": 0.25,
            "line_crossing_tolerance_pixels": 3.0,
            "minimum_signal_confidence": 0.60,
            "maximum_missed_frames": -1,
        },
    ],
)
def test_rejects_invalid_configuration(
    keyword_arguments,
) -> None:
    with pytest.raises(ValueError):
        RedLightCrossingDetector(**keyword_arguments)
