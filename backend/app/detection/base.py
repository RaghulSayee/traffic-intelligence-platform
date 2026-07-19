from typing import Protocol

from app.detection.types import DetectionResult
from app.pipelines.base import VideoFrame


class ObjectDetector(Protocol):
    """Interface implemented by object-detection providers."""

    model_name: str
    device: str

    def predict(
        self,
        frame: VideoFrame,
    ) -> DetectionResult:
        """Detect relevant objects in one BGR video frame."""

        ...
