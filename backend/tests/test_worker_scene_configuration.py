from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.workers.video_worker import (
    VideoProcessingWorker,
)


def test_missing_camera_returns_empty_scene() -> None:
    scene = VideoProcessingWorker._parse_scene_configuration(None)

    assert scene.schema_version == "1.0"
    assert scene.lanes == []
    assert scene.stop_lines == []


def test_worker_parses_valid_camera_scene() -> None:
    camera = SimpleNamespace(
        id=uuid4(),
        configuration={
            "road_name": "Test Road",
            "scene": {
                "schema_version": "1.0",
                "enabled_violations": [
                    "wrong_way",
                ],
                "lanes": [
                    {
                        "lane_id": "lane-1",
                        "polygon": {
                            "points": [
                                {
                                    "x": 0.1,
                                    "y": 0.1,
                                },
                                {
                                    "x": 0.4,
                                    "y": 0.1,
                                },
                                {
                                    "x": 0.5,
                                    "y": 0.9,
                                },
                                {
                                    "x": 0.05,
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
            },
        },
    )

    scene = VideoProcessingWorker._parse_scene_configuration(camera)

    assert scene.enabled_violations[0].value == ("wrong_way")

    assert len(scene.lanes) == 1
    assert scene.lanes[0].lane_id == "lane-1"


def test_worker_rejects_invalid_camera_scene() -> None:
    camera_id = uuid4()

    camera = SimpleNamespace(
        id=camera_id,
        configuration={
            "scene": {
                "schema_version": "1.0",
                "lanes": [
                    {
                        "lane_id": "lane-1",
                        "polygon": {
                            "points": [
                                {
                                    "x": 0.1,
                                    "y": 0.1,
                                },
                                {
                                    "x": 0.2,
                                    "y": 0.2,
                                },
                            ]
                        },
                        "allowed_direction": {
                            "x": 0.0,
                            "y": -1.0,
                        },
                    }
                ],
            }
        },
    )

    with pytest.raises(
        RuntimeError,
        match=str(camera_id),
    ):
        (VideoProcessingWorker._parse_scene_configuration(camera))
