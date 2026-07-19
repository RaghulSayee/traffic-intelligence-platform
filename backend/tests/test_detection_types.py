from app.detection.types import (
    BoundingBox,
    Detection,
    DetectionResult,
)


def test_bounding_box_properties() -> None:
    bounding_box = BoundingBox(
        x1=10,
        y1=20,
        x2=110,
        y2=220,
    )

    assert bounding_box.width == 100
    assert bounding_box.height == 200
    assert bounding_box.area == 20_000
    assert bounding_box.center == (60, 120)


def test_bounding_box_is_clipped_to_image() -> None:
    bounding_box = BoundingBox(
        x1=-20,
        y1=-10,
        x2=700,
        y2=500,
    )

    clipped = bounding_box.clipped(
        image_width=640,
        image_height=360,
    )

    assert clipped == BoundingBox(
        x1=0,
        y1=0,
        x2=640,
        y2=360,
    )


def test_detection_result_counts_classes() -> None:
    bounding_box = BoundingBox(
        x1=10,
        y1=10,
        x2=100,
        y2=100,
    )

    result = DetectionResult(
        detections=(
            Detection(
                class_id=0,
                class_name="person",
                confidence=0.95,
                bounding_box=bounding_box,
                model_name="test-model",
            ),
            Detection(
                class_id=0,
                class_name="person",
                confidence=0.90,
                bounding_box=bounding_box,
                model_name="test-model",
            ),
            Detection(
                class_id=3,
                class_name="motorcycle",
                confidence=0.88,
                bounding_box=bounding_box,
                model_name="test-model",
            ),
        ),
        inference_time_ms=20,
        image_width=640,
        image_height=360,
    )

    assert result.count == 3

    assert result.count_by_class() == {
        "person": 2,
        "motorcycle": 1,
    }
