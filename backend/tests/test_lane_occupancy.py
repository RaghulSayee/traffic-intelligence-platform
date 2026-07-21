import pytest

from app.detection.types import BoundingBox
from app.reasoning.lane_occupancy import (
    LaneOccupancyAnalyzer,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)
from app.tracking.types import TrackedObject


IMAGE_WIDTH = 640
IMAGE_HEIGHT = 360


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
    track_id: int = 1,
    x1: float = 220.0,
    x2: float = 320.0,
    velocity_x: float = 80.0,
    velocity_y: float = 0.0,
    confirmed: bool = True,
) -> TrackedObject:
    return TrackedObject(
        track_id=track_id,
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
        velocity_y=velocity_y,
    )


def create_analyzer(
    *,
    minimum_speed: float = 15.0,
    boundary_tolerance: float = 12.0,
) -> LaneOccupancyAnalyzer:
    return LaneOccupancyAnalyzer(
        minimum_speed_pixels_per_second=(minimum_speed),
        boundary_tolerance_pixels=(boundary_tolerance),
    )


def analyze(
    analyzer: LaneOccupancyAnalyzer,
    *,
    track: TrackedObject,
    scene: CameraSceneConfiguration | None = None,
):
    return analyzer.analyze(
        tracks=(track,),
        scene=(scene if scene is not None else create_scene()),
        image_width=IMAGE_WIDTH,
        image_height=IMAGE_HEIGHT,
    )


def test_vehicle_inside_lane_is_assigned() -> None:
    result = analyze(
        create_analyzer(),
        track=create_track(),
    )

    assert len(result.observations) == 1

    observation = result.observations[0]

    assert observation.lane_id == "lane-1"
    assert observation.nearest_lane_id == "lane-1"
    assert observation.outside_configured_lanes is False
    assert observation.violation_candidate is False


def test_vehicle_far_outside_lane_is_candidate() -> None:
    result = analyze(
        create_analyzer(),
        track=create_track(
            x1=450.0,
            x2=550.0,
        ),
    )

    observation = result.observations[0]

    assert observation.lane_id is None
    assert observation.nearest_lane_id == "lane-1"
    assert observation.inside_monitoring_zone is True
    assert observation.outside_configured_lanes is True
    assert observation.within_boundary_tolerance is False
    assert observation.violation_candidate is True

    assert observation.distance_to_nearest_lane_pixels > 12.0


def test_vehicle_near_lane_edge_is_tolerated() -> None:
    result = analyze(
        create_analyzer(
            boundary_tolerance=12.0,
        ),
        track=create_track(
            x1=340.0,
            x2=440.0,
        ),
    )

    observation = result.observations[0]

    assert observation.lane_id is None
    assert observation.within_boundary_tolerance is True
    assert observation.violation_candidate is False

    assert observation.distance_to_nearest_lane_pixels <= 12.0


def test_slow_vehicle_outside_lane_is_not_candidate() -> None:
    result = analyze(
        create_analyzer(),
        track=create_track(
            x1=450.0,
            x2=550.0,
            velocity_x=5.0,
        ),
    )

    observation = result.observations[0]

    assert observation.speed_pixels_per_second == pytest.approx(5.0)

    assert observation.violation_candidate is False


def test_vehicle_outside_monitoring_zone_is_ignored() -> None:
    result = analyze(
        create_analyzer(),
        track=create_track(
            x1=590.0,
            x2=630.0,
        ),
    )

    observation = result.observations[0]

    assert observation.inside_monitoring_zone is False
    assert observation.violation_candidate is False


def test_disabled_lane_rule_returns_no_observations() -> None:
    result = analyze(
        create_analyzer(),
        track=create_track(),
        scene=create_scene(enabled=False),
    )

    assert result.observations == ()
    assert result.violation_candidates == ()


def test_unconfirmed_vehicle_is_ignored() -> None:
    result = analyze(
        create_analyzer(),
        track=create_track(confirmed=False),
    )

    assert result.observations == ()
