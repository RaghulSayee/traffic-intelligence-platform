from app.detection.base import ObjectDetector
from app.detection.helmet import HelmetDetector
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
    PipelineSummary,
    VideoContext,
)
from app.reasoning.annotation import (
    annotate_reasoning,
)
from app.reasoning.helmet_rider import (
    HelmetRiderAssociator,
)
from app.reasoning.no_helmet import (
    NoHelmetTransitionType,
    NoHelmetViolationDetector,
)
from app.reasoning.rider_motorcycle import (
    RiderMotorcycleAssociator,
)
from app.reasoning.temporal_rider import (
    TemporalRiderAssociationSmoother,
)
from app.reasoning.triple_riding import (
    TripleRidingTransitionType,
    TripleRidingViolationDetector,
)
from app.tracking.annotation import annotate_tracks
from app.tracking.multi_object import MultiObjectTracker


class YoloTrafficPipeline:
    """Detect, track, and reason about traffic objects."""

    name = "yolo-traffic-pipeline"
    version = "0.5.0"

    def __init__(
        self,
        *,
        detector: ObjectDetector,
        helmet_detector: HelmetDetector,
        tracker: MultiObjectTracker,
        rider_associator: RiderMotorcycleAssociator,
        rider_smoother: TemporalRiderAssociationSmoother,
        helmet_rider_associator: HelmetRiderAssociator,
        triple_riding_detector: TripleRidingViolationDetector,
        no_helmet_detector: NoHelmetViolationDetector,
        frame_stride: int,
    ) -> None:
        if frame_stride <= 0:
            raise ValueError("Frame stride must be greater than zero.")

        self.detector = detector
        self.helmet_detector = helmet_detector

        self.tracker = tracker

        self.rider_associator = rider_associator
        self.rider_smoother = rider_smoother

        self.helmet_rider_associator = helmet_rider_associator

        self.triple_riding_detector = triple_riding_detector

        self.no_helmet_detector = no_helmet_detector

        self.frame_stride = frame_stride

        self.frames_seen = 0
        self.frames_analyzed = 0

        self.total_detections = 0
        self.total_inference_time_ms = 0.0

        self.total_helmet_detections = 0
        self.total_helmet_inference_time_ms = 0.0

        self.detection_class_counts: dict[
            str,
            int,
        ] = {}

        self.helmet_detection_class_counts: dict[
            str,
            int,
        ] = {}

        self.unique_track_ids_by_class: dict[
            str,
            set[int],
        ] = {}

        self.maximum_concurrent_confirmed_tracks = 0
        self.removed_track_count = 0

        self.total_frame_rider_associations = 0
        self.maximum_confirmed_rider_associations = 0
        self.maximum_riders_on_motorcycle = 0

        self.total_helmet_rider_associations = 0
        self.maximum_active_no_helmet_violations = 0

        self.triple_riding_event_count = 0
        self.no_helmet_event_count = 0

        self.unique_triple_riding_motorcycle_ids: set[int] = set()

        self.unique_no_helmet_person_ids: set[int] = set()

    def start(
        self,
        context: VideoContext,
    ) -> None:
        """Reset all state before processing a video."""

        self.tracker.reset()
        self.rider_smoother.reset()

        self.triple_riding_detector.reset()
        self.no_helmet_detector.reset()

        self.frames_seen = 0
        self.frames_analyzed = 0

        self.total_detections = 0
        self.total_inference_time_ms = 0.0

        self.total_helmet_detections = 0
        self.total_helmet_inference_time_ms = 0.0

        self.detection_class_counts = {}
        self.helmet_detection_class_counts = {}

        self.unique_track_ids_by_class = {}

        self.maximum_concurrent_confirmed_tracks = 0
        self.removed_track_count = 0

        self.total_frame_rider_associations = 0
        self.maximum_confirmed_rider_associations = 0
        self.maximum_riders_on_motorcycle = 0

        self.total_helmet_rider_associations = 0
        self.maximum_active_no_helmet_violations = 0

        self.triple_riding_event_count = 0
        self.no_helmet_event_count = 0

        self.unique_triple_riding_motorcycle_ids = set()
        self.unique_no_helmet_person_ids = set()

    def process_frame(
        self,
        packet: FramePacket,
    ) -> FrameAnalysis:
        """Analyze one sampled video frame."""

        self.frames_seen += 1

        should_analyze = (packet.frame_number - 1) % self.frame_stride == 0

        if not should_analyze:
            return FrameAnalysis(
                analyzed=False,
            )

        detection_result = self.detector.predict(packet.image)

        helmet_detection_result = self.helmet_detector.predict(packet.image)

        tracking_result = self.tracker.update(
            detections=detection_result.detections,
            timestamp_seconds=(packet.timestamp_seconds),
        )

        frame_associations = self.rider_associator.associate(tracking_result.tracks)

        temporal_associations = self.rider_smoother.update(frame_associations)

        helmet_association_result = self.helmet_rider_associator.associate(
            tracks=tracking_result.tracks,
            rider_associations=(temporal_associations.associations),
            helmet_detections=(helmet_detection_result.detections),
        )

        triple_riding_result = self.triple_riding_detector.update(
            frame_number=packet.frame_number,
            timestamp_seconds=(packet.timestamp_seconds),
            associations=(temporal_associations),
        )

        no_helmet_result = self.no_helmet_detector.update(
            frame_number=packet.frame_number,
            timestamp_seconds=(packet.timestamp_seconds),
            associations=(helmet_association_result),
        )

        confirmed_tracks = tracking_result.confirmed_tracks

        confirmed_rider_associations = temporal_associations.confirmed_associations

        rider_counts = temporal_associations.rider_counts_by_motorcycle()

        detection_class_counts = detection_result.count_by_class()

        helmet_detection_class_counts = helmet_detection_result.count_by_class()

        confirmed_track_counts = tracking_result.count_by_class()

        self.frames_analyzed += 1

        self.total_detections += detection_result.count

        self.total_inference_time_ms += detection_result.inference_time_ms

        self.total_helmet_detections += helmet_detection_result.count

        self.total_helmet_inference_time_ms += helmet_detection_result.inference_time_ms

        self.removed_track_count += len(tracking_result.removed_track_ids)

        self.total_frame_rider_associations += len(frame_associations.associations)

        self.total_helmet_rider_associations += len(
            helmet_association_result.associations
        )

        self.maximum_concurrent_confirmed_tracks = max(
            self.maximum_concurrent_confirmed_tracks,
            len(confirmed_tracks),
        )

        self.maximum_confirmed_rider_associations = max(
            self.maximum_confirmed_rider_associations,
            len(confirmed_rider_associations),
        )

        self.maximum_riders_on_motorcycle = max(
            self.maximum_riders_on_motorcycle,
            max(
                rider_counts.values(),
                default=0,
            ),
        )

        self.maximum_active_no_helmet_violations = max(
            self.maximum_active_no_helmet_violations,
            len(no_helmet_result.active_violations),
        )

        self._merge_class_counts(
            destination=(self.detection_class_counts),
            frame_counts=detection_class_counts,
        )

        self._merge_class_counts(
            destination=(self.helmet_detection_class_counts),
            frame_counts=(helmet_detection_class_counts),
        )

        for track in confirmed_tracks:
            track_ids = self.unique_track_ids_by_class.setdefault(
                track.class_name,
                set(),
            )

            track_ids.add(track.track_id)

        for transition in triple_riding_result.transitions:
            if transition.transition_type != TripleRidingTransitionType.STARTED:
                continue

            self.triple_riding_event_count += 1

            self.unique_triple_riding_motorcycle_ids.add(transition.motorcycle_track_id)

        for transition in no_helmet_result.transitions:
            if transition.transition_type != NoHelmetTransitionType.STARTED:
                continue

            self.no_helmet_event_count += 1

            self.unique_no_helmet_person_ids.add(transition.person_track_id)

        track_annotated_frame = annotate_tracks(
            packet.image,
            tracking_result.tracks,
        )

        annotated_frame = annotate_reasoning(
            track_annotated_frame,
            tracks=tracking_result.tracks,
            associations=(temporal_associations.associations),
            violations=(triple_riding_result.states),
            helmet_associations=(helmet_association_result.associations),
            no_helmet_violations=(no_helmet_result.states),
        )

        return FrameAnalysis(
            analyzed=True,
            detections=(detection_result.detections),
            helmet_detections=(helmet_detection_result.detections),
            tracks=tracking_result.tracks,
            rider_associations=(temporal_associations.associations),
            helmet_rider_associations=(helmet_association_result.associations),
            triple_riding_states=(triple_riding_result.states),
            triple_riding_transitions=(triple_riding_result.transitions),
            no_helmet_states=(no_helmet_result.states),
            no_helmet_transitions=(no_helmet_result.transitions),
            annotated_frame=annotated_frame,
            metrics={
                "frame_number": (packet.frame_number),
                "inference_time_ms": (detection_result.inference_time_ms),
                "helmet_inference_time_ms": (helmet_detection_result.inference_time_ms),
                "detection_count": (detection_result.count),
                "helmet_detection_count": (helmet_detection_result.count),
                "detection_class_counts": (detection_class_counts),
                "helmet_detection_class_counts": (helmet_detection_class_counts),
                "visible_track_count": len(tracking_result.tracks),
                "confirmed_track_count": len(confirmed_tracks),
                "active_track_count": (tracking_result.active_track_count),
                "confirmed_track_counts": (confirmed_track_counts),
                "unique_track_counts": (self._unique_track_counts()),
                "frame_rider_association_count": len(frame_associations.associations),
                "confirmed_rider_association_count": len(confirmed_rider_associations),
                "helmet_rider_association_count": len(
                    helmet_association_result.associations
                ),
                "rider_counts_by_motorcycle": {
                    str(motorcycle_id): count
                    for motorcycle_id, count in rider_counts.items()
                },
                "active_triple_riding_count": len(
                    triple_riding_result.active_violations
                ),
                "triple_riding_transition_count": len(triple_riding_result.transitions),
                "active_no_helmet_count": len(no_helmet_result.active_violations),
                "no_helmet_transition_count": len(no_helmet_result.transitions),
                "removed_track_ids": list(tracking_result.removed_track_ids),
                "removed_rider_pairs": [
                    list(pair) for pair in temporal_associations.removed_pairs
                ],
            },
        )

    def finish(self) -> PipelineSummary:
        """Return video-level processing statistics."""

        average_inference_time_ms = 0.0
        average_helmet_inference_time_ms = 0.0

        if self.frames_analyzed > 0:
            average_inference_time_ms = (
                self.total_inference_time_ms / self.frames_analyzed
            )

            average_helmet_inference_time_ms = (
                self.total_helmet_inference_time_ms / self.frames_analyzed
            )

        unique_track_counts = self._unique_track_counts()

        return PipelineSummary(
            metrics={
                "pipeline_name": self.name,
                "pipeline_version": self.version,
                "detector_model": (self.detector.model_name),
                "detector_device": (self.detector.device),
                "helmet_detector_enabled": (self.helmet_detector.enabled),
                "helmet_detector_model": (self.helmet_detector.model_name),
                "helmet_detector_device": (self.helmet_detector.device),
                "frame_stride": self.frame_stride,
                "frames_seen": self.frames_seen,
                "frames_analyzed": (self.frames_analyzed),
                "total_detection_occurrences": (self.total_detections),
                "total_helmet_detection_occurrences": (self.total_helmet_detections),
                "detection_class_counts": (self.detection_class_counts),
                "helmet_detection_class_counts": (self.helmet_detection_class_counts),
                "average_inference_time_ms": (average_inference_time_ms),
                "average_helmet_inference_time_ms": (average_helmet_inference_time_ms),
                "unique_confirmed_tracks": sum(unique_track_counts.values()),
                "unique_track_counts_by_class": (unique_track_counts),
                "maximum_concurrent_confirmed_tracks": (
                    self.maximum_concurrent_confirmed_tracks
                ),
                "removed_track_count": (self.removed_track_count),
                "total_frame_rider_associations": (self.total_frame_rider_associations),
                "maximum_confirmed_rider_associations": (
                    self.maximum_confirmed_rider_associations
                ),
                "maximum_riders_on_motorcycle": (self.maximum_riders_on_motorcycle),
                "total_helmet_rider_associations": (
                    self.total_helmet_rider_associations
                ),
                "maximum_active_no_helmet_violations": (
                    self.maximum_active_no_helmet_violations
                ),
                "triple_riding_event_count": (self.triple_riding_event_count),
                "unique_triple_riding_motorcycles": len(
                    self.unique_triple_riding_motorcycle_ids
                ),
                "triple_riding_motorcycle_track_ids": sorted(
                    self.unique_triple_riding_motorcycle_ids
                ),
                "no_helmet_event_count": (self.no_helmet_event_count),
                "unique_no_helmet_riders": len(self.unique_no_helmet_person_ids),
                "no_helmet_person_track_ids": sorted(self.unique_no_helmet_person_ids),
            }
        )

    def _unique_track_counts(
        self,
    ) -> dict[str, int]:
        """Count confirmed track IDs by object class."""

        return {
            class_name: len(track_ids)
            for class_name, track_ids in sorted(self.unique_track_ids_by_class.items())
        }

    @staticmethod
    def _merge_class_counts(
        *,
        destination: dict[str, int],
        frame_counts: dict[str, int],
    ) -> None:
        """Add frame-level class counts to totals."""

        for class_name, count in frame_counts.items():
            destination[class_name] = (
                destination.get(
                    class_name,
                    0,
                )
                + count
            )
