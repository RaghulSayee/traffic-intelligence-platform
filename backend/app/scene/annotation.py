import cv2
import numpy as np

from app.pipelines.base import VideoFrame
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)
from app.scene.geometry import (
    direction_endpoint,
    normalized_line_to_pixels,
    normalized_polygon_to_pixels,
    polygon_centroid,
)


def annotate_scene(
    frame: VideoFrame,
    scene: CameraSceneConfiguration | None,
) -> VideoFrame:
    """Draw configured road-scene geometry over a frame."""

    annotated = frame.copy()

    if scene is None:
        return annotated

    image_height, image_width = annotated.shape[:2]

    if scene.monitoring_zone is not None:
        monitoring_points = normalized_polygon_to_pixels(
            scene.monitoring_zone,
            image_width=image_width,
            image_height=image_height,
        )

        _draw_polygon(
            annotated,
            points=monitoring_points,
            color=(255, 255, 0),
            thickness=2,
        )

        _draw_label(
            annotated,
            label="MONITORING ZONE",
            position=monitoring_points[0],
            color=(255, 255, 0),
        )

    for lane in scene.lanes:
        lane_points = normalized_polygon_to_pixels(
            lane.polygon,
            image_width=image_width,
            image_height=image_height,
        )

        _draw_polygon(
            annotated,
            points=lane_points,
            color=(255, 120, 0),
            thickness=2,
        )

        center = polygon_centroid(lane_points)

        arrow_length = max(
            min(
                image_width,
                image_height,
            )
            * 0.10,
            25.0,
        )

        arrow_end = direction_endpoint(
            origin=center,
            direction=lane.allowed_direction,
            length_pixels=arrow_length,
        )

        cv2.arrowedLine(
            annotated,
            center,
            arrow_end,
            (255, 120, 0),
            thickness=3,
            line_type=cv2.LINE_AA,
            tipLength=0.25,
        )

        label = lane.name or lane.lane_id

        if lane.speed_limit_kph is not None:
            label += f" {lane.speed_limit_kph:g} km/h"

        _draw_label(
            annotated,
            label=label,
            position=lane_points[0],
            color=(255, 120, 0),
        )

    for region in scene.traffic_light_regions:
        region_points = normalized_polygon_to_pixels(
            region.polygon,
            image_width=image_width,
            image_height=image_height,
        )

        _draw_polygon(
            annotated,
            points=region_points,
            color=(0, 0, 255),
            thickness=3,
        )

        _draw_label(
            annotated,
            label=(region.name or region.region_id),
            position=region_points[0],
            color=(0, 0, 255),
        )

    for stop_line in scene.stop_lines:
        start, end = normalized_line_to_pixels(
            stop_line.line,
            image_width=image_width,
            image_height=image_height,
        )

        cv2.line(
            annotated,
            start,
            end,
            (0, 255, 255),
            thickness=4,
            lineType=cv2.LINE_AA,
        )

        _draw_label(
            annotated,
            label=stop_line.stop_line_id,
            position=start,
            color=(0, 255, 255),
        )

    for segment in scene.speed_calibration_segments:
        start, end = normalized_line_to_pixels(
            segment.line,
            image_width=image_width,
            image_height=image_height,
        )

        cv2.line(
            annotated,
            start,
            end,
            (255, 0, 255),
            thickness=3,
            lineType=cv2.LINE_AA,
        )

        midpoint = (
            round((start[0] + end[0]) / 2),
            round((start[1] + end[1]) / 2),
        )

        _draw_label(
            annotated,
            label=(f"{segment.distance_meters:g} m"),
            position=midpoint,
            color=(255, 0, 255),
        )

    return annotated


def _draw_polygon(
    frame: VideoFrame,
    *,
    points: tuple[
        tuple[int, int],
        ...,
    ],
    color: tuple[int, int, int],
    thickness: int,
) -> None:
    polygon = np.array(
        points,
        dtype=np.int32,
    ).reshape((-1, 1, 2))

    cv2.polylines(
        frame,
        [polygon],
        isClosed=True,
        color=color,
        thickness=thickness,
        lineType=cv2.LINE_AA,
    )


def _draw_label(
    frame: VideoFrame,
    *,
    label: str,
    position: tuple[int, int],
    color: tuple[int, int, int],
) -> None:
    x, y = position

    y = max(
        y - 6,
        16,
    )

    cv2.putText(
        frame,
        label,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        color,
        thickness=2,
        lineType=cv2.LINE_AA,
    )
