import cv2

from app.detection.types import Detection
from app.pipelines.base import VideoFrame


def annotate_detections(
    frame: VideoFrame,
    detections: tuple[Detection, ...],
) -> VideoFrame:
    """Return a copy of the frame with detection overlays."""

    annotated_frame = frame.copy()

    for detection in detections:
        x1, y1, x2, y2 = detection.bounding_box.as_integer_tuple()

        label = f"{detection.class_name} {detection.confidence:.2f}"

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
            (x1 + 4, max(y1 - 5, text_height)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            thickness=2,
            lineType=cv2.LINE_AA,
        )

    return annotated_frame
