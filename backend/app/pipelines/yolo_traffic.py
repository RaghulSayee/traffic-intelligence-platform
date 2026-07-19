from app.detection.base import ObjectDetector
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
    PipelineSummary,
    VideoContext,
)
from app.reasoning.annotation import (
    annotate_reasoning,
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
    version = "0.4.0"

    def __init__(
        self,
        *,
        detector: ObjectDetector,
        tracker: MultiObjectTracker,
        rider_associator: RiderMotorcycleAssociator,
        rider_smoother: TemporalRiderAssociationSmoother,
        triple_riding_detector: TripleRidingViolationDetector,
        frame_stride: int,
    ) -> None:
        if frame_stride <= 0:
            raise ValueError("Frame stride must be greater than zero.")

        self.detector = detector
        self.tracker = tracker

        self.rider_associator = rider_associator
        self.rider_smoother = rider_smoother

        self.triple_riding_detector = triple_riding_detector

        self.frame_stride = frame_stride

        self.frames_seen = 0
        self.frames_analyzed = 0

        self.total_detections = 0
        self.total_inference_time_ms = 0.0

        self.detection_class_counts: dict[
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

        self.triple_riding_event_count = 0

        self.unique_triple_riding_motorcycle_ids: set[int] = set()

    def start(
        self,
        context: VideoContext,
    ) -> None:
        """Reset all state before processing a video."""

        self.tracker.reset()
        self.rider_smoother.reset()
        self.triple_riding_detector.reset()

        self.frames_seen = 0
        self.frames_analyzed = 0

        self.total_detections = 0
        self.total_inference_time_ms = 0.0

        self.detection_class_counts = {}
        self.unique_track_ids_by_class = {}

        self.maximum_concurrent_confirmed_tracks = 0
        self.removed_track_count = 0

        self.total_frame_rider_associations = 0
        self.maximum_confirmed_rider_associations = 0
        self.maximum_riders_on_motorcycle = 0

        self.triple_riding_event_count = 0

        self.unique_triple_riding_motorcycle_ids = set()

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

        tracking_result = self.tracker.update(
            detections=detection_result.detections,
            timestamp_seconds=packet.timestamp_seconds,
        )

        frame_associations = self.rider_associator.associate(tracking_result.tracks)

        temporal_associations = self.rider_smoother.update(frame_associations)

        triple_riding_result = self.triple_riding_detector.update(
            frame_number=packet.frame_number,
            timestamp_seconds=(packet.timestamp_seconds),
            associations=(temporal_associations),
        )

        confirmed_tracks = tracking_result.confirmed_tracks

        confirmed_rider_associations = temporal_associations.confirmed_associations

        rider_counts = temporal_associations.rider_counts_by_motorcycle()

        detection_class_counts = detection_result.count_by_class()

        confirmed_track_counts = tracking_result.count_by_class()

        self.frames_analyzed += 1

        self.total_detections += detection_result.count

        self.total_inference_time_ms += detection_result.inference_time_ms

        self.removed_track_count += len(tracking_result.removed_track_ids)

        self.total_frame_rider_associations += len(frame_associations.associations)

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

        for class_name, count in detection_class_counts.items():
            self.detection_class_counts[class_name] = (
                self.detection_class_counts.get(
                    class_name,
                    0,
                )
                + count
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

        track_annotated_frame = annotate_tracks(
            packet.image,
            tracking_result.tracks,
        )

        annotated_frame = annotate_reasoning(
            track_annotated_frame,
            tracks=tracking_result.tracks,
            associations=(temporal_associations.associations),
            violations=(triple_riding_result.states),
        )

        return FrameAnalysis(
            analyzed=True,
            detections=detection_result.detections,
            tracks=tracking_result.tracks,
            rider_associations=(temporal_associations.associations),
            triple_riding_states=(triple_riding_result.states),
            triple_riding_transitions=(triple_riding_result.transitions),
            annotated_frame=annotated_frame,
            metrics={
                "frame_number": packet.frame_number,
                "inference_time_ms": (detection_result.inference_time_ms),
                "detection_count": (detection_result.count),
                "detection_class_counts": (detection_class_counts),
                "visible_track_count": len(tracking_result.tracks),
                "confirmed_track_count": len(confirmed_tracks),
                "active_track_count": (tracking_result.active_track_count),
                "confirmed_track_counts": (confirmed_track_counts),
                "unique_track_counts": (self._unique_track_counts()),
                "frame_rider_association_count": len(frame_associations.associations),
                "confirmed_rider_association_count": (
                    len(confirmed_rider_associations)
                ),
                "rider_counts_by_motorcycle": {
                    str(motorcycle_id): count
                    for motorcycle_id, count in rider_counts.items()
                },
                "active_triple_riding_count": len(
                    triple_riding_result.active_violations
                ),
                "triple_riding_transition_count": len(triple_riding_result.transitions),
                "removed_track_ids": list(tracking_result.removed_track_ids),
                "removed_rider_pairs": [
                    list(pair) for pair in temporal_associations.removed_pairs
                ],
            },
        )

    def finish(self) -> PipelineSummary:
        """Return video-level processing statistics."""

        average_inference_time_ms = 0.0

        if self.frames_analyzed > 0:
            average_inference_time_ms = (
                self.total_inference_time_ms / self.frames_analyzed
            )

        unique_track_counts = self._unique_track_counts()

        return PipelineSummary(
            metrics={
                "pipeline_name": self.name,
                "pipeline_version": self.version,
                "detector_model": (self.detector.model_name),
                "detector_device": (self.detector.device),
                "frame_stride": self.frame_stride,
                "frames_seen": self.frames_seen,
                "frames_analyzed": (self.frames_analyzed),
                "total_detection_occurrences": (self.total_detections),
                "detection_class_counts": (self.detection_class_counts),
                "average_inference_time_ms": (average_inference_time_ms),
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
                "triple_riding_event_count": (self.triple_riding_event_count),
                "unique_triple_riding_motorcycles": (
                    len(self.unique_triple_riding_motorcycle_ids)
                ),
                "triple_riding_motorcycle_track_ids": (
                    sorted(self.unique_triple_riding_motorcycle_ids)
                ),
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
