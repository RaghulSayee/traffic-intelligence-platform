import cv2

from app.pipelines.base import VideoFrame
from app.tracking.types import TrackedObject


def annotate_tracks(
    frame: VideoFrame,
    tracks: tuple[TrackedObject, ...],
) -> VideoFrame:
    """Draw persistent IDs and bounding boxes."""

    annotated_frame = frame.copy()

    image_height, image_width = annotated_frame.shape[:2]

    for track in tracks:
        box = track.bounding_box.clipped(
            image_width=image_width,
            image_height=image_height,
        )

        x1, y1, x2, y2 = box.as_integer_tuple()

        lifecycle = "" if track.confirmed else " tentative"

        label = (
            f"ID {track.track_id} {track.class_name} {track.confidence:.2f}{lifecycle}"
        )

        cv2.rectangle(
            annotated_frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            thickness=2,
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
            annotated_frame,
            (x1, text_top),
            (x1 + text_width + 8, y1),
            (0, 255, 0),
            thickness=-1,
        )

        cv2.putText(
            annotated_frame,
            label,
            (
                x1 + 4,
                max(
                    y1 - 5,
                    text_height,
                ),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            thickness=2,
            lineType=cv2.LINE_AA,
        )

    return annotated_frame
