import time
from collections.abc import Collection

from ultralytics import YOLO

from app.detection.base import ObjectDetector
from app.detection.device import resolve_inference_device
from app.detection.types import (
    BoundingBox,
    Detection,
    DetectionResult,
)
from app.pipelines.base import VideoFrame


DEFAULT_TRAFFIC_CLASSES = frozenset(
    {
        "person",
        "bicycle",
        "car",
        "motorcycle",
        "bus",
        "truck",
        "traffic light",
    }
)


class UltralyticsObjectDetector(ObjectDetector):
    """Detect traffic objects using an Ultralytics YOLO model."""

    def __init__(
        self,
        *,
        model_path: str,
        device: str,
        confidence_threshold: float,
        iou_threshold: float,
        image_size: int,
        allowed_classes: Collection[str] | None = None,
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0 and 1.")

        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError("IoU threshold must be between 0 and 1.")

        if image_size <= 0:
            raise ValueError("Image size must be greater than zero.")

        self.model_name = model_path
        self.device = resolve_inference_device(device)

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.image_size = image_size

        self.allowed_classes = frozenset(allowed_classes or DEFAULT_TRAFFIC_CLASSES)

        self.model = YOLO(model_path)

    def predict(
        self,
        frame: VideoFrame,
    ) -> DetectionResult:
        """Detect and normalize traffic objects from one frame."""

        image_height, image_width = frame.shape[:2]

        started_at = time.perf_counter()

        predictions = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            imgsz=self.image_size,
            device=self.device,
            verbose=False,
        )

        inference_time_ms = (time.perf_counter() - started_at) * 1000.0

        if not predictions:
            return DetectionResult(
                detections=(),
                inference_time_ms=inference_time_ms,
                image_width=image_width,
                image_height=image_height,
            )

        prediction = predictions[0]

        if prediction.boxes is None:
            return DetectionResult(
                detections=(),
                inference_time_ms=inference_time_ms,
                image_width=image_width,
                image_height=image_height,
            )

        xyxy_values = prediction.boxes.xyxy.detach().cpu().numpy()

        confidence_values = prediction.boxes.conf.detach().cpu().numpy()

        class_values = prediction.boxes.cls.detach().cpu().numpy()

        detections: list[Detection] = []

        for box_values, confidence, class_value in zip(
            xyxy_values,
            confidence_values,
            class_values,
            strict=True,
        ):
            class_id = int(class_value)

            class_name = str(prediction.names[class_id])

            if class_name not in self.allowed_classes:
                continue

            x1, y1, x2, y2 = (float(value) for value in box_values)

            bounding_box = BoundingBox(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
            ).clipped(
                image_width=image_width,
                image_height=image_height,
            )

            if bounding_box.area <= 0:
                continue

            detections.append(
                Detection(
                    class_id=class_id,
                    class_name=class_name,
                    confidence=float(confidence),
                    bounding_box=bounding_box,
                    model_name=self.model_name,
                )
            )

        detections.sort(
            key=lambda detection: detection.confidence,
            reverse=True,
        )

        return DetectionResult(
            detections=tuple(detections),
            inference_time_ms=inference_time_ms,
            image_width=image_width,
            image_height=image_height,
        )
