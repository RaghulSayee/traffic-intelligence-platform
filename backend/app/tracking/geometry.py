import numpy as np
from numpy.typing import NDArray

from app.detection.types import BoundingBox


def intersection_over_union(
    first: BoundingBox,
    second: BoundingBox,
) -> float:
    """Calculate Intersection over Union for two boxes."""

    intersection_x1 = max(
        first.x1,
        second.x1,
    )

    intersection_y1 = max(
        first.y1,
        second.y1,
    )

    intersection_x2 = min(
        first.x2,
        second.x2,
    )

    intersection_y2 = min(
        first.y2,
        second.y2,
    )

    intersection_width = max(
        intersection_x2 - intersection_x1,
        0.0,
    )

    intersection_height = max(
        intersection_y2 - intersection_y1,
        0.0,
    )

    intersection_area = intersection_width * intersection_height

    union_area = first.area + second.area - intersection_area

    if union_area <= 0:
        return 0.0

    return float(intersection_area / union_area)


def build_iou_matrix(
    track_boxes: list[BoundingBox],
    detection_boxes: list[BoundingBox],
) -> NDArray[np.float64]:
    """Build pairwise IoU values for tracks and detections."""

    matrix = np.zeros(
        (
            len(track_boxes),
            len(detection_boxes),
        ),
        dtype=np.float64,
    )

    for track_index, track_box in enumerate(track_boxes):
        for detection_index, detection_box in enumerate(detection_boxes):
            matrix[
                track_index,
                detection_index,
            ] = intersection_over_union(
                track_box,
                detection_box,
            )

    return matrix
