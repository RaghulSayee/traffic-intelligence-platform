from math import hypot

import cv2

from app.pipelines.base import VideoFrame
from app.reasoning.wrong_way import (
    WrongWayViolationSnapshot,
)
from app.tracking.types import TrackedObject


def annotate_wrong_way(
    frame: VideoFrame,
    *,
    tracks: tuple[TrackedObject, ...],
    violations: tuple[
        WrongWayViolationSnapshot,
        ...,
    ],
) -> VideoFrame:
    """Draw wrong-way candidates and confirmed violations."""

    annotated = frame.copy()

    image_height, image_width = annotated.shape[:2]

    tracks_by_id = {track.track_id: track for track in tracks}

    for violation in violations:
        track = tracks_by_id.get(violation.track_id)

        if track is None:
            continue

        box = track.bounding_box.clipped(
            image_width=image_width,
            image_height=image_height,
        )

        x1, y1, x2, y2 = box.as_integer_tuple()

        if violation.confirmed:
            color = (
                0,
                0,
                255,
            )

            label = (
                f"WRONG WAY | {violation.lane_id} "
                f"| {violation.speed_pixels_per_second:.1f}px/s"
            )

            thickness = 4

        else:
            color = (
                0,
                165,
                255,
            )

            label = f"wrong-way candidate {violation.consecutive_violation_frames}"

            thickness = 2

        cv2.rectangle(
            annotated,
            (
                x1,
                y1,
            ),
            (
                x2,
                y2,
            ),
            color,
            thickness=thickness,
        )

        center_x, center_y = track.bounding_box.center

        speed = hypot(
            violation.velocity_x,
            violation.velocity_y,
        )

        if speed > 0:
            arrow_length = min(
                max(
                    speed * 0.35,
                    25.0,
                ),
                100.0,
            )

            direction_x = violation.velocity_x / speed

            direction_y = violation.velocity_y / speed

            arrow_end = (
                int(center_x + direction_x * arrow_length),
                int(center_y + direction_y * arrow_length),
            )

            cv2.arrowedLine(
                annotated,
                (
                    int(center_x),
                    int(center_y),
                ),
                arrow_end,
                color,
                thickness=3,
                line_type=cv2.LINE_AA,
                tipLength=0.25,
            )

        text_size, baseline = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            2,
        )

        text_width, text_height = text_size

        text_top = max(
            y1 - text_height - baseline - 8,
            0,
        )

        cv2.rectangle(
            annotated,
            (
                x1,
                text_top,
            ),
            (
                min(
                    x1 + text_width + 10,
                    image_width,
                ),
                y1,
            ),
            color,
            thickness=-1,
        )

        cv2.putText(
            annotated,
            label,
            (
                x1 + 5,
                max(
                    y1 - 5,
                    text_height,
                ),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (
                255,
                255,
                255,
            ),
            thickness=2,
            lineType=cv2.LINE_AA,
        )

    return annotated
