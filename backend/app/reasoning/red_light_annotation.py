from __future__ import annotations

import cv2

from app.pipelines.base import VideoFrame
from app.reasoning.red_light import (
    RedLightCrossingObservation,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)
from app.scene.geometry import (
    normalized_line_to_pixels,
)


def annotate_red_light_crossings(
    frame: VideoFrame,
    *,
    scene: CameraSceneConfiguration | None,
    crossings: tuple[
        RedLightCrossingObservation,
        ...,
    ],
) -> VideoFrame:
    """Draw stop-line crossings and red-light violations."""

    annotated = frame.copy()

    if scene is None or not crossings:
        return annotated

    stop_lines_by_id = {
        stop_line.stop_line_id: stop_line for stop_line in scene.stop_lines
    }

    image_height, image_width = annotated.shape[:2]

    for crossing in crossings:
        stop_line = stop_lines_by_id.get(crossing.stop_line_id)

        if stop_line is None:
            continue

        line_start, line_end = normalized_line_to_pixels(
            stop_line.line,
            image_width=image_width,
            image_height=image_height,
        )

        color = (0, 0, 255) if crossing.is_violation else (0, 165, 255)

        cv2.line(
            annotated,
            line_start,
            line_end,
            color,
            5,
            cv2.LINE_AA,
        )

        previous_anchor = (
            round(crossing.previous_anchor_x_normalized * max(image_width - 1, 1)),
            round(crossing.previous_anchor_y_normalized * max(image_height - 1, 1)),
        )

        current_anchor = (
            round(crossing.anchor_x_normalized * max(image_width - 1, 1)),
            round(crossing.anchor_y_normalized * max(image_height - 1, 1)),
        )

        cv2.line(
            annotated,
            previous_anchor,
            current_anchor,
            color,
            3,
            cv2.LINE_AA,
        )

        cv2.circle(
            annotated,
            previous_anchor,
            5,
            color,
            -1,
            cv2.LINE_AA,
        )

        cv2.circle(
            annotated,
            current_anchor,
            7,
            color,
            -1,
            cv2.LINE_AA,
        )

        status = (
            "RED LIGHT VIOLATION" if crossing.is_violation else "STOP-LINE CROSSING"
        )

        label = (
            f"{status} "
            f"track={crossing.track_id} "
            f"signal={crossing.signal_state.value} "
            f"rule={crossing.rule_confidence:.2f}"
        )

        label_x = min(
            line_start[0],
            line_end[0],
        )

        label_y = max(
            min(
                line_start[1],
                line_end[1],
            )
            - 12,
            25,
        )

        cv2.putText(
            annotated,
            label,
            (
                label_x,
                label_y,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    return annotated
