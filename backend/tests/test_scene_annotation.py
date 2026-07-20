import numpy as np

from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)
from app.scene.annotation import annotate_scene


def test_scene_annotation_draws_configuration() -> None:
    frame = np.zeros(
        (
            200,
            300,
            3,
        ),
        dtype=np.uint8,
    )

    scene = CameraSceneConfiguration(
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
                            "x": 0.2,
                            "y": 0.2,
                        },
                        {
                            "x": 0.5,
                            "y": 0.2,
                        },
                        {
                            "x": 0.6,
                            "y": 0.9,
                        },
                        {
                            "x": 0.1,
                            "y": 0.9,
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

    annotated = annotate_scene(
        frame,
        scene,
    )

    assert annotated.shape == frame.shape

    assert int(np.count_nonzero(annotated)) > 0

    assert int(np.count_nonzero(frame)) == 0


def test_empty_scene_preserves_blank_frame() -> None:
    frame = np.zeros(
        (
            100,
            100,
            3,
        ),
        dtype=np.uint8,
    )

    annotated = annotate_scene(
        frame,
        CameraSceneConfiguration(),
    )

    assert int(np.count_nonzero(annotated)) == 0
