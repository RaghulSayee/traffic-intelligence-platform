import numpy as np

from app.reasoning.red_light import (
    RedLightCrossingObservation,
)
from app.reasoning.red_light_annotation import (
    annotate_red_light_crossings,
)
from app.reasoning.traffic_light_state import (
    TrafficLightState,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)


def create_scene() -> CameraSceneConfiguration:
    return CameraSceneConfiguration(
        enabled_violations=[
            "red_light",
        ],
        lanes=[
            {
                "lane_id": "lane-1",
                "polygon": {
                    "points": [
                        {"x": 0.10, "y": 0.10},
                        {"x": 0.90, "y": 0.10},
                        {"x": 0.90, "y": 0.90},
                        {"x": 0.10, "y": 0.90},
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
                "polygon": {
                    "points": [
                        {"x": 0.05, "y": 0.05},
                        {"x": 0.15, "y": 0.05},
                        {"x": 0.15, "y": 0.20},
                        {"x": 0.05, "y": 0.20},
                    ]
                },
            }
        ],
        stop_lines=[
            {
                "stop_line_id": "stop-1",
                "lane_id": "lane-1",
                "traffic_light_region_id": "signal-1",
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
        ],
    )


def create_crossing() -> RedLightCrossingObservation:
    return RedLightCrossingObservation(
        track_id=1,
        class_name="car",
        stop_line_id="stop-1",
        lane_id="lane-1",
        traffic_light_region_id="signal-1",
        signal_state=TrafficLightState.RED,
        signal_confidence=0.95,
        previous_frame_number=1,
        frame_number=2,
        timestamp_seconds=0.10,
        previous_anchor_x_normalized=0.50,
        previous_anchor_y_normalized=0.40,
        anchor_x_normalized=0.50,
        anchor_y_normalized=0.60,
        previous_signed_distance_pixels=-10.0,
        signed_distance_pixels=10.0,
        crossing_depth_pixels=20.0,
        velocity_x=0.0,
        velocity_y=100.0,
        speed_pixels_per_second=100.0,
        direction_cosine=1.0,
        detection_confidence=0.90,
        rule_confidence=0.95,
        is_violation=True,
    )


def test_draws_red_light_crossing() -> None:
    frame = np.zeros(
        (
            200,
            200,
            3,
        ),
        dtype=np.uint8,
    )

    result = annotate_red_light_crossings(
        frame,
        scene=create_scene(),
        crossings=(create_crossing(),),
    )

    assert np.any(result != frame)


def test_empty_crossings_return_unchanged_copy() -> None:
    frame = np.zeros(
        (
            100,
            100,
            3,
        ),
        dtype=np.uint8,
    )

    result = annotate_red_light_crossings(
        frame,
        scene=create_scene(),
        crossings=(),
    )

    assert np.array_equal(
        result,
        frame,
    )

    assert result is not frame
