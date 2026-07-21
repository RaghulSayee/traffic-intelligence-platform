from pathlib import Path

from app.core.config import Settings
from app.detection.base import ObjectDetector
from app.detection.helmet import (
    DisabledHelmetDetector,
    HelmetDetector,
    UltralyticsHelmetDetector,
)
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
from app.reasoning.lane_occupancy import (
    LaneOccupancyAnalyzer,
)
from app.reasoning.lane_violation import (
    LaneViolationDetector,
)
from app.reasoning.wrong_way import (
    WrongWayViolationDetector,
)
from app.tracking.multi_object import (
    MultiObjectTracker,
)
from app.reasoning.helmet_rider import (
    HelmetRiderAssociator,
)
from app.reasoning.no_helmet import (
    NoHelmetViolationDetector,
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

        self._helmet_detector: HelmetDetector | None = None

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

    def get_helmet_detector(
        self,
    ) -> HelmetDetector:
        """Create and cache the configured helmet detector."""

        if self._helmet_detector is not None:
            return self._helmet_detector

        if not self.settings.helmet_detector_enabled:
            self._helmet_detector = DisabledHelmetDetector()

            return self._helmet_detector

        model_path = Path(self.settings.helmet_detector_model_path).expanduser()

        if not model_path.is_file():
            raise FileNotFoundError(
                "Helmet detection is enabled, but "
                f"the model was not found: '{model_path}'."
            )

        self._helmet_detector = UltralyticsHelmetDetector(
            model_path=str(model_path),
            device=(self.settings.helmet_detector_device),
            confidence_threshold=(self.settings.helmet_detector_confidence_threshold),
            iou_threshold=(self.settings.helmet_detector_iou_threshold),
            image_size=(self.settings.helmet_detector_image_size),
        )

        return self._helmet_detector

    def _create_yolo_pipeline(
        self,
    ) -> YoloTrafficPipeline:
        """Create fresh stateful components for one video."""

        return YoloTrafficPipeline(
            detector=self._get_traffic_detector(),
            helmet_detector=self.get_helmet_detector(),
            tracker=self._create_tracker(),
            rider_associator=(self._create_rider_associator()),
            rider_smoother=(self._create_rider_smoother()),
            helmet_rider_associator=(self._create_helmet_rider_associator()),
            triple_riding_detector=(self._create_triple_riding_detector()),
            no_helmet_detector=(self._create_no_helmet_detector()),
            wrong_way_detector=self._create_wrong_way_detector(),
            lane_violation_detector=(self._create_lane_violation_detector()),
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

    def _create_helmet_rider_associator(
        self,
    ) -> HelmetRiderAssociator:
        """Create helmet-to-rider spatial reasoning."""

        return HelmetRiderAssociator(
            head_height_ratio=(self.settings.helmet_head_height_ratio),
            head_width_expansion_ratio=(
                self.settings.helmet_head_width_expansion_ratio
            ),
            minimum_score=(self.settings.helmet_rider_minimum_score),
        )

    def _create_no_helmet_detector(
        self,
    ) -> NoHelmetViolationDetector:
        """Create temporal no-helmet state."""

        return NoHelmetViolationDetector(
            confirmation_frames=(self.settings.no_helmet_confirmation_frames),
            maximum_missed_frames=(self.settings.no_helmet_maximum_missed_frames),
            confidence_alpha=(self.settings.no_helmet_confidence_alpha),
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

    def _create_lane_violation_detector(
        self,
    ) -> LaneViolationDetector:
        """Create lane occupancy and temporal reasoning."""

        occupancy_analyzer = LaneOccupancyAnalyzer(
            minimum_speed_pixels_per_second=(
                self.settings.lane_violation_minimum_speed_pixels_per_second
            ),
            boundary_tolerance_pixels=(
                self.settings.lane_violation_boundary_tolerance_pixels
            ),
        )

        return LaneViolationDetector(
            occupancy_analyzer=occupancy_analyzer,
            confirmation_frames=(self.settings.lane_violation_confirmation_frames),
            maximum_missed_frames=(self.settings.lane_violation_maximum_missed_frames),
        )

    def _create_wrong_way_detector(
        self,
    ) -> WrongWayViolationDetector:
        """Create lane-direction violation reasoning."""

        return WrongWayViolationDetector(
            minimum_speed_pixels_per_second=(
                self.settings.wrong_way_minimum_speed_pixels_per_second
            ),
            opposite_cosine_threshold=(
                self.settings.wrong_way_opposite_cosine_threshold
            ),
            confirmation_frames=(self.settings.wrong_way_confirmation_frames),
            maximum_missed_frames=(self.settings.wrong_way_maximum_missed_frames),
        )
