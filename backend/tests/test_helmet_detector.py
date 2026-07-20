import numpy as np
import pytest

from app.detection.helmet import (
    DisabledHelmetDetector,
    canonicalize_helmet_class_name,
    normalize_model_label,
)


@pytest.mark.parametrize(
    ("source_name", "expected"),
    [
        ("Helmet", "helmet"),
        ("With Helmet", "helmet"),
        ("wearing-helmet", "helmet"),
        ("No Helmet", "no_helmet"),
        ("WITHOUT_HELMET", "no_helmet"),
        (
            "Not Wearing Helmet",
            "no_helmet",
        ),
    ],
)
def test_canonicalizes_common_helmet_labels(
    source_name: str,
    expected: str,
) -> None:
    assert canonicalize_helmet_class_name(source_name) == expected


def test_returns_none_for_unknown_class() -> None:
    assert canonicalize_helmet_class_name("motorcycle") is None


def test_normalizes_model_label() -> None:
    assert normalize_model_label("  No-Helmet Rider  ") == "no_helmet_rider"


def test_disabled_detector_returns_empty_result() -> None:
    frame = np.zeros(
        (
            40,
            60,
            3,
        ),
        dtype=np.uint8,
    )

    detector = DisabledHelmetDetector()

    result = detector.predict(frame)

    assert detector.enabled is False
    assert result.detections == ()
    assert result.count == 0
    assert result.image_width == 60
    assert result.image_height == 40
    assert result.inference_time_ms == 0.0
