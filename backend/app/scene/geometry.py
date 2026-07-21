from __future__ import annotations

from math import hypot

from app.schemas.camera_scene import (
    NormalizedDirection,
    NormalizedLine,
    NormalizedPoint,
    NormalizedPolygon,
)


PixelPoint = tuple[int, int]
PixelLine = tuple[PixelPoint, PixelPoint]


def normalized_point_to_pixel(
    point: NormalizedPoint,
    *,
    image_width: int,
    image_height: int,
) -> PixelPoint:
    """Convert one normalized point into image coordinates."""

    _validate_image_dimensions(
        image_width=image_width,
        image_height=image_height,
    )

    maximum_x = image_width - 1
    maximum_y = image_height - 1

    return (
        round(point.x * maximum_x),
        round(point.y * maximum_y),
    )


def normalized_polygon_to_pixels(
    polygon: NormalizedPolygon,
    *,
    image_width: int,
    image_height: int,
) -> tuple[PixelPoint, ...]:
    """Convert a normalized polygon into pixel coordinates."""

    return tuple(
        normalized_point_to_pixel(
            point,
            image_width=image_width,
            image_height=image_height,
        )
        for point in polygon.points
    )


def normalized_line_to_pixels(
    line: NormalizedLine,
    *,
    image_width: int,
    image_height: int,
) -> PixelLine:
    """Convert a normalized line into pixel coordinates."""

    return (
        normalized_point_to_pixel(
            line.start,
            image_width=image_width,
            image_height=image_height,
        ),
        normalized_point_to_pixel(
            line.end,
            image_width=image_width,
            image_height=image_height,
        ),
    )


def polygon_centroid(
    points: tuple[PixelPoint, ...],
) -> PixelPoint:
    """Return the average center of polygon vertices."""

    if not points:
        raise ValueError("At least one polygon point is required.")

    return (
        round(sum(point[0] for point in points) / len(points)),
        round(sum(point[1] for point in points) / len(points)),
    )


def direction_endpoint(
    *,
    origin: PixelPoint,
    direction: NormalizedDirection,
    length_pixels: float,
) -> PixelPoint:
    """Create an arrow endpoint from a direction vector."""

    if length_pixels <= 0:
        raise ValueError("Direction length must be positive.")

    magnitude = hypot(
        direction.x,
        direction.y,
    )

    if magnitude == 0:
        raise ValueError("Direction vector cannot be zero.")

    normalized_x = direction.x / magnitude
    normalized_y = direction.y / magnitude

    return (
        round(origin[0] + normalized_x * length_pixels),
        round(origin[1] + normalized_y * length_pixels),
    )


def normalized_point_in_polygon(
    *,
    point: NormalizedPoint,
    polygon: NormalizedPolygon,
) -> bool:
    """Check whether a normalized point lies inside a polygon."""

    x = point.x
    y = point.y

    points = polygon.points

    inside = False

    previous_index = len(points) - 1

    for current_index, current in enumerate(points):
        previous = points[previous_index]

        crosses_vertical_position = (current.y > y) != (previous.y > y)

        if crosses_vertical_position:
            denominator = previous.y - current.y

            if denominator == 0:
                previous_index = current_index
                continue

            crossing_x = (previous.x - current.x) * (
                y - current.y
            ) / denominator + current.x

            if x < crossing_x:
                inside = not inside

        previous_index = current_index

    return inside


def _validate_image_dimensions(
    *,
    image_width: int,
    image_height: int,
) -> None:
    if image_width <= 0:
        raise ValueError("Image width must be positive.")

    if image_height <= 0:
        raise ValueError("Image height must be positive.")


FloatPoint = tuple[float, float]


def point_to_line_segment_distance(
    *,
    point: FloatPoint,
    start: FloatPoint,
    end: FloatPoint,
) -> float:
    """Return the shortest pixel distance to a line segment."""

    point_x, point_y = point
    start_x, start_y = start
    end_x, end_y = end

    segment_x = end_x - start_x
    segment_y = end_y - start_y

    segment_length_squared = segment_x * segment_x + segment_y * segment_y

    if segment_length_squared == 0:
        return hypot(
            point_x - start_x,
            point_y - start_y,
        )

    projection = (
        (point_x - start_x) * segment_x + (point_y - start_y) * segment_y
    ) / segment_length_squared

    projection = min(
        max(projection, 0.0),
        1.0,
    )

    nearest_x = start_x + projection * segment_x

    nearest_y = start_y + projection * segment_y

    return hypot(
        point_x - nearest_x,
        point_y - nearest_y,
    )


def point_to_polygon_edge_distance(
    *,
    point: FloatPoint,
    polygon: tuple[PixelPoint, ...],
) -> float:
    """Return the shortest pixel distance to a polygon edge."""

    if len(polygon) < 3:
        raise ValueError("A polygon requires at least three points.")

    distances = []

    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]

        distances.append(
            point_to_line_segment_distance(
                point=point,
                start=(
                    float(start[0]),
                    float(start[1]),
                ),
                end=(
                    float(end[0]),
                    float(end[1]),
                ),
            )
        )

    return min(distances)
