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
from app.tracking.multi_object import (
    MultiObjectTracker,
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

        if pipeline_name in {
            "traffic-violation-pipeline",
            "yolo-traffic-pipeline",
        }:
            return self._create_yolo_pipeline()

        raise ValueError(f"Unsupported pipeline: '{pipeline_name}'.")

    def _create_yolo_pipeline(
        self,
    ) -> YoloTrafficPipeline:
        """
        Create one stateful pipeline and tracker per video job.

        The detector is reused, but tracker state must never be
        shared between two videos.
        """

        return YoloTrafficPipeline(
            detector=self._get_traffic_detector(),
            tracker=self._create_tracker(),
            frame_stride=(self.settings.detector_frame_stride),
        )

    def _get_traffic_detector(
        self,
    ) -> ObjectDetector:
        """Create and cache one model per worker process."""

        if self._traffic_detector is None:
            self._traffic_detector = UltralyticsObjectDetector(
                model_path=(self.settings.detector_model_path),
                device=(self.settings.detector_device),
                confidence_threshold=(self.settings.detector_confidence_threshold),
                iou_threshold=(self.settings.detector_iou_threshold),
                image_size=(self.settings.detector_image_size),
            )

        return self._traffic_detector

    def _create_tracker(
        self,
    ) -> MultiObjectTracker:
        """Create fresh tracking state for one processing job."""

        return MultiObjectTracker(
            high_confidence_threshold=(self.settings.tracker_high_confidence_threshold),
            low_confidence_threshold=(self.settings.tracker_low_confidence_threshold),
            primary_iou_threshold=(self.settings.tracker_primary_iou_threshold),
            secondary_iou_threshold=(self.settings.tracker_secondary_iou_threshold),
            minimum_confirmed_hits=(self.settings.tracker_min_confirmed_hits),
            maximum_missed_frames=(self.settings.tracker_max_missed_frames),
            process_noise=(self.settings.tracker_process_noise),
            measurement_noise=(self.settings.tracker_measurement_noise),
        )
