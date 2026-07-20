import pytest

from app.schemas.camera_scene import (
    NormalizedDirection,
    NormalizedLine,
    NormalizedPoint,
    NormalizedPolygon,
)
from app.scene.geometry import (
    direction_endpoint,
    normalized_line_to_pixels,
    normalized_point_in_polygon,
    normalized_point_to_pixel,
)


def test_converts_normalized_point_to_pixel() -> None:
    result = normalized_point_to_pixel(
        NormalizedPoint(
            x=1.0,
            y=1.0,
        ),
        image_width=200,
        image_height=100,
    )

    assert result == (
        199,
        99,
    )


def test_converts_normalized_line() -> None:
    result = normalized_line_to_pixels(
        NormalizedLine(
            start=NormalizedPoint(
                x=0.0,
                y=0.5,
            ),
            end=NormalizedPoint(
                x=1.0,
                y=0.5,
            ),
        ),
        image_width=101,
        image_height=101,
    )

    assert result == (
        (
            0,
            50,
        ),
        (
            100,
            50,
        ),
    )


def test_point_is_inside_polygon() -> None:
    polygon = NormalizedPolygon(
        points=[
            NormalizedPoint(
                x=0.1,
                y=0.1,
            ),
            NormalizedPoint(
                x=0.9,
                y=0.1,
            ),
            NormalizedPoint(
                x=0.9,
                y=0.9,
            ),
            NormalizedPoint(
                x=0.1,
                y=0.9,
            ),
        ]
    )

    assert normalized_point_in_polygon(
        point=NormalizedPoint(
            x=0.5,
            y=0.5,
        ),
        polygon=polygon,
    )

    assert not normalized_point_in_polygon(
        point=NormalizedPoint(
            x=0.95,
            y=0.95,
        ),
        polygon=polygon,
    )


def test_direction_endpoint_normalizes_vector() -> None:
    result = direction_endpoint(
        origin=(
            100,
            100,
        ),
        direction=NormalizedDirection(
            x=0.0,
            y=-1.0,
        ),
        length_pixels=40,
    )

    assert result == (
        100,
        60,
    )


def test_rejects_invalid_image_dimensions() -> None:
    with pytest.raises(ValueError):
        normalized_point_to_pixel(
            NormalizedPoint(
                x=0.5,
                y=0.5,
            ),
            image_width=0,
            image_height=100,
        )
