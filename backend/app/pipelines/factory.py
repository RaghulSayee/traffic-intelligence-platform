from app.core.config import Settings
from app.detection.base import ObjectDetector
from app.detection.ultralytics_detector import (
    UltralyticsObjectDetector,
)
from app.pipelines.base import VideoAnalysisPipeline
from app.pipelines.baseline import (
    BaselineTrafficPipeline,
)
from app.pipelines.yolo_traffic import (
    YoloTrafficPipeline,
)


class VideoPipelineFactory:
    """Create configured video-analysis pipelines."""

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

        self._traffic_detector: ObjectDetector | None = None

    def create(
        self,
        pipeline_name: str,
    ) -> VideoAnalysisPipeline:
        """Create a pipeline using its registered name."""

        if pipeline_name == "baseline-traffic-pipeline":
            return BaselineTrafficPipeline()

        if pipeline_name == "traffic-violation-pipeline":
            return YoloTrafficPipeline(
                detector=self._get_traffic_detector(),
                frame_stride=(self.settings.detector_frame_stride),
            )

        if pipeline_name == "yolo-traffic-pipeline":
            return YoloTrafficPipeline(
                detector=self._get_traffic_detector(),
                frame_stride=(self.settings.detector_frame_stride),
            )

        raise ValueError(f"Unsupported pipeline: '{pipeline_name}'.")

    def _get_traffic_detector(
        self,
    ) -> ObjectDetector:
        """Create and cache one detector per worker."""

        if self._traffic_detector is None:
            self._traffic_detector = UltralyticsObjectDetector(
                model_path=(self.settings.detector_model_path),
                device=(self.settings.detector_device),
                confidence_threshold=(self.settings.detector_confidence_threshold),
                iou_threshold=(self.settings.detector_iou_threshold),
                image_size=(self.settings.detector_image_size),
            )

        return self._traffic_detector
