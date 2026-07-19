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
from app.reasoning.rider_motorcycle import (
    RiderMotorcycleAssociator,
)
from app.reasoning.temporal_rider import (
    TemporalRiderAssociationSmoother,
)
from app.reasoning.triple_riding import (
    TripleRidingViolationDetector,
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
        """Create fresh stateful components for one video."""

        return YoloTrafficPipeline(
            detector=self._get_traffic_detector(),
            tracker=self._create_tracker(),
            rider_associator=(self._create_rider_associator()),
            rider_smoother=(self._create_rider_smoother()),
            triple_riding_detector=(self._create_triple_riding_detector()),
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

    def _create_rider_associator(
        self,
    ) -> RiderMotorcycleAssociator:
        """Create frame-level relationship reasoning."""

        return RiderMotorcycleAssociator(
            minimum_score=(self.settings.rider_association_minimum_score),
            max_riders_per_motorcycle=(
                self.settings.rider_association_max_riders_per_motorcycle
            ),
            max_anchor_distance_ratio=(
                self.settings.rider_association_max_anchor_distance_ratio
            ),
            minimum_horizontal_overlap=(
                self.settings.rider_association_minimum_horizontal_overlap
            ),
            minimum_motion_speed=(self.settings.rider_association_minimum_motion_speed),
        )

    def _create_rider_smoother(
        self,
    ) -> TemporalRiderAssociationSmoother:
        """Create temporal relationship memory."""

        return TemporalRiderAssociationSmoother(
            confirmation_frames=(self.settings.rider_temporal_confirmation_frames),
            maximum_missed_frames=(self.settings.rider_temporal_max_missed_frames),
            score_alpha=(self.settings.rider_temporal_score_alpha),
        )

    def _create_triple_riding_detector(
        self,
    ) -> TripleRidingViolationDetector:
        """Create triple-riding lifecycle state."""

        return TripleRidingViolationDetector(
            minimum_riders=(self.settings.triple_riding_minimum_riders),
            confirmation_frames=(self.settings.triple_riding_confirmation_frames),
            maximum_missed_frames=(self.settings.triple_riding_maximum_missed_frames),
        )
