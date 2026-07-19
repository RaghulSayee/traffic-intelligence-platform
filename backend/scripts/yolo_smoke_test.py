import argparse
from pathlib import Path

import cv2

from app.core.config import get_settings
from app.detection.annotation import annotate_detections
from app.detection.ultralytics_detector import (
    UltralyticsObjectDetector,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Run YOLO traffic detection on one video frame.")
    )

    parser.add_argument(
        "--video",
        type=Path,
        required=True,
        help="Path to a traffic video.",
    )

    parser.add_argument(
        "--frame",
        type=int,
        default=0,
        help="Zero-based frame number to analyze.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("storage/evidence/yolo-smoke-test.jpg"),
        help="Destination for the annotated image.",
    )

    return parser.parse_args()


def read_video_frame(
    *,
    video_path: Path,
    frame_number: int,
):
    if frame_number < 0:
        raise ValueError("Frame number cannot be negative.")

    capture = cv2.VideoCapture(str(video_path))

    try:
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        capture.set(
            cv2.CAP_PROP_POS_FRAMES,
            frame_number,
        )

        successful_read, frame = capture.read()

        if not successful_read:
            raise RuntimeError(f"Could not read frame {frame_number}.")

        return frame

    finally:
        capture.release()


def main() -> None:
    arguments = parse_arguments()
    settings = get_settings()

    frame = read_video_frame(
        video_path=arguments.video,
        frame_number=arguments.frame,
    )

    detector = UltralyticsObjectDetector(
        model_path=settings.detector_model_path,
        device=settings.detector_device,
        confidence_threshold=(settings.detector_confidence_threshold),
        iou_threshold=settings.detector_iou_threshold,
        image_size=settings.detector_image_size,
    )

    print(f"Model: {detector.model_name}")
    print(f"Device: {detector.device}")

    result = detector.predict(frame)

    print(f"Inference time: {result.inference_time_ms:.2f} ms")

    print(f"Detections: {result.count}")
    print(f"Class counts: {result.count_by_class()}")

    for detection in result.detections:
        box = detection.bounding_box

        print(
            f"- {detection.class_name:<14} "
            f"confidence={detection.confidence:.3f} "
            f"box=({box.x1:.1f}, {box.y1:.1f}, "
            f"{box.x2:.1f}, {box.y2:.1f})"
        )

    annotated_frame = annotate_detections(
        frame,
        result.detections,
    )

    arguments.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    successful_write = cv2.imwrite(
        str(arguments.output),
        annotated_frame,
    )

    if not successful_write:
        raise RuntimeError(f"Could not save image to {arguments.output}.")

    print(f"Annotated image: {arguments.output}")


if __name__ == "__main__":
    main()
