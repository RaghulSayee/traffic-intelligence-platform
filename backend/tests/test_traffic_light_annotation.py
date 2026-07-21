import numpy as np

from app.reasoning.traffic_light_annotation import (
    annotate_traffic_light_states,
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


def test_draws_stable_traffic_light_state() -> None:
    frame = np.zeros(
        (
            200,
            200,
            3,
        ),
        dtype=np.uint8,
    )

    scene = CameraSceneConfiguration(
        enabled_violations=[
            "red_light",
        ],
        traffic_light_regions=[
            {
                "region_id": "signal-1",
                "name": "Main Signal",
                "polygon": {
                    "points": [
                        {
                            "x": 0.20,
                            "y": 0.10,
                        },
                        {
                            "x": 0.80,
                            "y": 0.10,
                        },
                        {
                            "x": 0.80,
                            "y": 0.90,
                        },
                        {
                            "x": 0.20,
                            "y": 0.90,
                        },
                    ]
                },
            }
        ],
    )

    state = StableTrafficLightSnapshot(
        region_id="signal-1",
        region_name="Main Signal",
        raw_state=TrafficLightState.RED,
        raw_confidence=0.95,
        stable_state=TrafficLightState.RED,
        stable_confidence=0.92,
        candidate_state=(TrafficLightState.UNKNOWN),
        candidate_confidence=0.0,
        consecutive_candidate_frames=0,
        unknown_frames=0,
        red_score=0.20,
        yellow_score=0.0,
        green_score=0.0,
        active_pixel_ratio=0.20,
        last_observed_frame=3,
        observed_this_frame=True,
    )

    result = annotate_traffic_light_states(
        frame,
        scene=scene,
        states=(state,),
    )

    assert np.any(result != frame)
