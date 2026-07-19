import pytest

from app.detection.types import BoundingBox
from app.tracking.geometry import (
    intersection_over_union,
)


def test_identical_boxes_have_perfect_iou() -> None:
    box = BoundingBox(
        x1=10,
        y1=20,
        x2=110,
        y2=120,
    )

    assert intersection_over_union(
        box,
        box,
    ) == pytest.approx(1.0)


def test_non_overlapping_boxes_have_zero_iou() -> None:
    first = BoundingBox(
        x1=0,
        y1=0,
        x2=100,
        y2=100,
    )

    second = BoundingBox(
        x1=200,
        y1=200,
        x2=300,
        y2=300,
    )

    assert (
        intersection_over_union(
            first,
            second,
        )
        == 0.0
    )


def test_partially_overlapping_boxes() -> None:
    first = BoundingBox(
        x1=0,
        y1=0,
        x2=100,
        y2=100,
    )

    second = BoundingBox(
        x1=50,
        y1=0,
        x2=150,
        y2=100,
    )

    # Intersection = 5,000
    # Union = 15,000
    assert intersection_over_union(
        first,
        second,
    ) == pytest.approx(1.0 / 3.0)
