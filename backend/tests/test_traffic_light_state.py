import cv2
import numpy as np
import pytest

from app.reasoning.traffic_light_state import (
    TrafficLightState,
    TrafficLightStateClassifier,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)


IMAGE_WIDTH = 200
IMAGE_HEIGHT = 200


def create_scene(
    *,
    enabled: bool = True,
) -> CameraSceneConfiguration:
    return CameraSceneConfiguration(
        enabled_violations=(["red_light"] if enabled else []),
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


def create_classifier(
    *,
    minimum_active_pixel_ratio: float = 0.01,
    dominance_ratio: float = 1.25,
) -> TrafficLightStateClassifier:
    return TrafficLightStateClassifier(
        minimum_saturation=80,
        minimum_value=100,
        minimum_active_pixel_ratio=(minimum_active_pixel_ratio),
        dominance_ratio=dominance_ratio,
    )


def create_frame(
    color: tuple[
        int,
        int,
        int,
    ]
    | None,
) -> np.ndarray:
    frame = np.zeros(
        (
            IMAGE_HEIGHT,
            IMAGE_WIDTH,
            3,
        ),
        dtype=np.uint8,
    )

    if color is not None:
        cv2.circle(
            frame,
            (
                100,
                100,
            ),
            22,
            color,
            thickness=-1,
        )

    return frame


@pytest.mark.parametrize(
    (
        "color",
        "expected_state",
    ),
    [
        (
            (
                0,
                0,
                255,
            ),
            TrafficLightState.RED,
        ),
        (
            (
                0,
                255,
                255,
            ),
            TrafficLightState.YELLOW,
        ),
        (
            (
                0,
                255,
                0,
            ),
            TrafficLightState.GREEN,
        ),
    ],
)
def test_classifies_signal_color(
    color,
    expected_state,
) -> None:
    classifier = create_classifier()

    result = classifier.classify(
        frame=create_frame(color),
        scene=create_scene(),
    )

    assert len(result.observations) == 1

    observation = result.observations[0]

    assert observation.state == expected_state

    assert observation.confidence == (pytest.approx(1.0))

    assert observation.active_pixel_ratio > 0.01


def test_dark_signal_is_unknown() -> None:
    classifier = create_classifier()

    result = classifier.classify(
        frame=create_frame(
            (
                0,
                0,
                50,
            )
        ),
        scene=create_scene(),
    )

    observation = result.observations[0]

    assert observation.state == TrafficLightState.UNKNOWN

    assert observation.confidence == 0.0


def test_empty_signal_region_is_unknown() -> None:
    classifier = create_classifier()

    result = classifier.classify(
        frame=create_frame(None),
        scene=create_scene(),
    )

    observation = result.observations[0]

    assert observation.state == TrafficLightState.UNKNOWN

    assert observation.active_pixel_count == 0


def test_ambiguous_red_and_green_is_unknown() -> None:
    classifier = create_classifier(
        dominance_ratio=1.25,
    )

    frame = create_frame(None)

    cv2.circle(
        frame,
        (
            80,
            100,
        ),
        20,
        (
            0,
            0,
            255,
        ),
        thickness=-1,
    )

    cv2.circle(
        frame,
        (
            120,
            100,
        ),
        20,
        (
            0,
            255,
            0,
        ),
        thickness=-1,
    )

    result = classifier.classify(
        frame=frame,
        scene=create_scene(),
    )

    assert result.observations[0].state == TrafficLightState.UNKNOWN


def test_disabled_red_light_rule_returns_empty_result() -> None:
    classifier = create_classifier()

    result = classifier.classify(
        frame=create_frame(
            (
                0,
                0,
                255,
            )
        ),
        scene=create_scene(enabled=False),
    )

    assert result.observations == ()


def test_missing_scene_returns_empty_result() -> None:
    classifier = create_classifier()

    result = classifier.classify(
        frame=create_frame(
            (
                0,
                0,
                255,
            )
        ),
        scene=None,
    )

    assert result.observations == ()


def test_counts_regions_by_state() -> None:
    classifier = create_classifier()

    result = classifier.classify(
        frame=create_frame(
            (
                0,
                0,
                255,
            )
        ),
        scene=create_scene(),
    )

    assert result.count_by_state() == {
        "red": 1,
    }

    assert result.get_region("signal-1") is not None

    assert result.get_region("missing") is None


@pytest.mark.parametrize(
    (
        "keyword_arguments",
        "message",
    ),
    [
        (
            {
                "minimum_saturation": -1,
                "minimum_value": 100,
                "minimum_active_pixel_ratio": 0.01,
                "dominance_ratio": 1.25,
            },
            "saturation",
        ),
        (
            {
                "minimum_saturation": 80,
                "minimum_value": 300,
                "minimum_active_pixel_ratio": 0.01,
                "dominance_ratio": 1.25,
            },
            "value",
        ),
        (
            {
                "minimum_saturation": 80,
                "minimum_value": 100,
                "minimum_active_pixel_ratio": 0.0,
                "dominance_ratio": 1.25,
            },
            "pixel ratio",
        ),
        (
            {
                "minimum_saturation": 80,
                "minimum_value": 100,
                "minimum_active_pixel_ratio": 0.01,
                "dominance_ratio": 0.9,
            },
            "(?i)dominance",
        ),
    ],
)
def test_rejects_invalid_configuration(
    keyword_arguments,
    message,
) -> None:
    with pytest.raises(
        ValueError,
        match=message,
    ):
        TrafficLightStateClassifier(**keyword_arguments)
