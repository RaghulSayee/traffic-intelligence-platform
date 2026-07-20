import re
import time
from collections.abc import Mapping
from typing import Protocol

from ultralytics import YOLO

from app.detection.base import ObjectDetector
from app.detection.device import resolve_inference_device
from app.detection.types import (
    BoundingBox,
    Detection,
    DetectionResult,
)
from app.pipelines.base import VideoFrame


HELMET_CLASS_NAME = "helmet"
NO_HELMET_CLASS_NAME = "no_helmet"

SUPPORTED_HELMET_CLASSES = frozenset(
    {
        HELMET_CLASS_NAME,
        NO_HELMET_CLASS_NAME,
    }
)

DEFAULT_HELMET_CLASS_ALIASES = {
    "helmet": HELMET_CLASS_NAME,
    "with_helmet": HELMET_CLASS_NAME,
    "wearing_helmet": HELMET_CLASS_NAME,
    "helmet_on": HELMET_CLASS_NAME,
    "safe": HELMET_CLASS_NAME,
    "no_helmet": NO_HELMET_CLASS_NAME,
    "without_helmet": NO_HELMET_CLASS_NAME,
    "not_wearing_helmet": NO_HELMET_CLASS_NAME,
    "helmet_off": NO_HELMET_CLASS_NAME,
    "non_helmet": NO_HELMET_CLASS_NAME,
}


class HelmetDetector(ObjectDetector, Protocol):
    """Interface implemented by helmet-detection providers."""

    enabled: bool


def normalize_model_label(
    value: str,
) -> str:
    """Normalize a model class label for alias matching."""

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        value.strip().lower(),
    ).strip("_")


def canonicalize_helmet_class_name(
    value: str,
    *,
    aliases: Mapping[str, str] | None = None,
) -> str | None:
    """Convert a model-specific class name into our canonical labels."""

    normalized_value = normalize_model_label(value)

    configured_aliases = (
        aliases if aliases is not None else DEFAULT_HELMET_CLASS_ALIASES
    )

    canonical_name = configured_aliases.get(normalized_value)

    if canonical_name not in SUPPORTED_HELMET_CLASSES:
        return None

    return canonical_name


class DisabledHelmetDetector:
    """Return no detections when helmet analysis is disabled."""

    enabled = False
    model_name = "helmet-detector-disabled"
    device = "disabled"

    def predict(
        self,
        frame: VideoFrame,
    ) -> DetectionResult:
        """Return an empty detection result."""

        image_height, image_width = frame.shape[:2]

        return DetectionResult(
            detections=(),
            inference_time_ms=0.0,
            image_width=image_width,
            image_height=image_height,
        )


class UltralyticsHelmetDetector:
    """Detect helmet and no-helmet regions using a custom YOLO model."""

    enabled = True

    def __init__(
        self,
        *,
        model_path: str,
        device: str,
        confidence_threshold: float,
        iou_threshold: float,
        image_size: int,
        class_aliases: Mapping[str, str] | None = None,
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

        aliases = dict(DEFAULT_HELMET_CLASS_ALIASES)

        if class_aliases:
            for source_name, target_name in class_aliases.items():
                normalized_source = normalize_model_label(source_name)

                normalized_target = normalize_model_label(target_name)

                if normalized_target not in SUPPORTED_HELMET_CLASSES:
                    raise ValueError(
                        "Helmet class aliases must map to 'helmet' or 'no_helmet'."
                    )

                aliases[normalized_source] = normalized_target

        self.class_aliases = aliases
        self.model = YOLO(model_path)

    def predict(
        self,
        frame: VideoFrame,
    ) -> DetectionResult:
        """Detect and normalize helmet-related objects."""

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
            return self._empty_result(
                inference_time_ms=inference_time_ms,
                image_width=image_width,
                image_height=image_height,
            )

        prediction = predictions[0]

        if prediction.boxes is None:
            return self._empty_result(
                inference_time_ms=inference_time_ms,
                image_width=image_width,
                image_height=image_height,
            )

        xyxy_values = prediction.boxes.xyxy.detach().cpu().numpy()

        confidence_values = prediction.boxes.conf.detach().cpu().numpy()

        class_values = prediction.boxes.cls.detach().cpu().numpy()

        detections: list[Detection] = []

        for (
            box_values,
            confidence,
            class_value,
        ) in zip(
            xyxy_values,
            confidence_values,
            class_values,
            strict=True,
        ):
            class_id = int(class_value)

            original_class_name = str(prediction.names[class_id])

            class_name = canonicalize_helmet_class_name(
                original_class_name,
                aliases=self.class_aliases,
            )

            if class_name is None:
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

    @staticmethod
    def _empty_result(
        *,
        inference_time_ms: float,
        image_width: int,
        image_height: int,
    ) -> DetectionResult:
        """Build an empty detector response."""

        return DetectionResult(
            detections=(),
            inference_time_ms=inference_time_ms,
            image_width=image_width,
            image_height=image_height,
        )
