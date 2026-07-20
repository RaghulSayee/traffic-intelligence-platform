import pytest
from pydantic import ValidationError

from app.schemas.camera_scene import (
    CameraSceneConfiguration,
    NormalizedDirection,
    NormalizedLine,
    NormalizedPoint,
    NormalizedPolygon,
)


def point(
    x: float,
    y: float,
) -> dict[str, float]:
    return {
        "x": x,
        "y": y,
    }


def test_normalized_point_rejects_out_of_bounds() -> None:
    with pytest.raises(ValidationError):
        NormalizedPoint(
            x=1.2,
            y=0.5,
        )


def test_polygon_requires_three_distinct_points() -> None:
    with pytest.raises(ValidationError):
        NormalizedPolygon(
            points=[
                NormalizedPoint(
                    x=0.1,
                    y=0.1,
                ),
                NormalizedPoint(
                    x=0.1,
                    y=0.1,
                ),
                NormalizedPoint(
                    x=0.2,
                    y=0.2,
                ),
            ]
        )


def test_line_rejects_identical_endpoints() -> None:
    with pytest.raises(ValidationError):
        NormalizedLine(
            start=NormalizedPoint(
                x=0.5,
                y=0.5,
            ),
            end=NormalizedPoint(
                x=0.5,
                y=0.5,
            ),
        )


def test_direction_rejects_zero_vector() -> None:
    with pytest.raises(ValidationError):
        NormalizedDirection(
            x=0.0,
            y=0.0,
        )


def test_scene_rejects_duplicate_lane_ids() -> None:
    lane = {
        "lane_id": "lane-1",
        "polygon": {
            "points": [
                point(0.1, 0.1),
                point(0.4, 0.1),
                point(0.4, 0.9),
                point(0.1, 0.9),
            ]
        },
        "allowed_direction": {
            "x": 0.0,
            "y": 1.0,
        },
    }

    with pytest.raises(ValidationError):
        CameraSceneConfiguration(
            lanes=[
                lane,
                lane,
            ]
        )


def test_scene_rejects_unknown_stop_line_reference() -> None:
    with pytest.raises(ValidationError):
        CameraSceneConfiguration(
            stop_lines=[
                {
                    "stop_line_id": "stop-1",
                    "lane_id": "missing-lane",
                    "line": {
                        "start": point(
                            0.2,
                            0.5,
                        ),
                        "end": point(
                            0.8,
                            0.5,
                        ),
                    },
                }
            ]
        )


def test_valid_scene_configuration() -> None:
    scene = CameraSceneConfiguration(
        enabled_violations=[
            "wrong_way",
            "red_light",
            "speeding",
        ],
        monitoring_zone={
            "points": [
                point(0.05, 0.05),
                point(0.95, 0.05),
                point(0.95, 0.95),
                point(0.05, 0.95),
            ]
        },
        lanes=[
            {
                "lane_id": "northbound",
                "name": "Northbound Lane",
                "polygon": {
                    "points": [
                        point(0.1, 0.2),
                        point(0.45, 0.2),
                        point(0.55, 0.95),
                        point(0.05, 0.95),
                    ]
                },
                "allowed_direction": {
                    "x": 0.0,
                    "y": -1.0,
                },
                "speed_limit_kph": 40,
            }
        ],
        traffic_light_regions=[
            {
                "region_id": "signal-1",
                "polygon": {
                    "points": [
                        point(0.70, 0.05),
                        point(0.80, 0.05),
                        point(0.80, 0.20),
                        point(0.70, 0.20),
                    ]
                },
            }
        ],
        stop_lines=[
            {
                "stop_line_id": "stop-1",
                "lane_id": "northbound",
                "traffic_light_region_id": "signal-1",
                "line": {
                    "start": point(
                        0.1,
                        0.55,
                    ),
                    "end": point(
                        0.5,
                        0.55,
                    ),
                },
            }
        ],
    )

    assert scene.schema_version == "1.0"
    assert scene.lanes[0].lane_id == "northbound"

    serialized = scene.model_dump(mode="json")

    assert serialized["enabled_violations"][0] == "wrong_way"
