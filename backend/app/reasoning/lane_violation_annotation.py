from __future__ import annotations

import cv2

from app.pipelines.base import VideoFrame
from app.reasoning.lane_violation import (
    LaneViolationSnapshot,
)
from app.tracking.types import TrackedObject


def annotate_lane_violations(
    frame: VideoFrame,
    *,
    tracks: tuple[TrackedObject, ...],
    violations: tuple[
        LaneViolationSnapshot,
        ...,
    ],
) -> VideoFrame:
    """Draw candidate and confirmed lane violations."""

    annotated = frame.copy()

    tracks_by_id = {track.track_id: track for track in tracks}

    image_height, image_width = annotated.shape[:2]

    for violation in violations:
        track = tracks_by_id.get(violation.track_id)

        if track is None:
            continue

        if violation.confirmed:
            color = (
                0,
                0,
                255,
            )

            label_prefix = "LANE VIOLATION"
            thickness = 3

        else:
            color = (
                0,
                165,
                255,
            )

            label_prefix = "LANE CANDIDATE"
            thickness = 2

        x1, y1, x2, y2 = track.bounding_box.as_integer_tuple()

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
            thickness,
        )

        anchor_x = round(
            violation.anchor_x_normalized
            * max(
                image_width - 1,
                1,
            )
        )

        anchor_y = round(
            violation.anchor_y_normalized
            * max(
                image_height - 1,
                1,
            )
        )

        cv2.circle(
            annotated,
            (
                anchor_x,
                anchor_y,
            ),
            7,
            color,
            thickness=-1,
        )

        nearest_lane = violation.nearest_lane_id or "none"

        distance = violation.distance_to_nearest_lane_pixels

        distance_label = f"{distance:.1f}px" if distance is not None else "unknown"

        label = (
            f"{label_prefix} "
            f"#{violation.track_id} "
            f"near={nearest_lane} "
            f"d={distance_label}"
        )

        text_y = max(
            y1 - 10,
            24,
        )

        cv2.putText(
            annotated,
            label,
            (
                x1,
                text_y,
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    return annotated
