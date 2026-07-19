from app.detection.base import ObjectDetector
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
    PipelineSummary,
    VideoContext,
)
from app.tracking.annotation import annotate_tracks
from app.tracking.multi_object import MultiObjectTracker


class YoloTrafficPipeline:
    """Detect and track traffic objects across sampled frames."""

    name = "yolo-traffic-pipeline"
    version = "0.3.0"

    def __init__(
        self,
        *,
        detector: ObjectDetector,
        tracker: MultiObjectTracker,
        frame_stride: int,
    ) -> None:
        if frame_stride <= 0:
            raise ValueError("Frame stride must be greater than zero.")

        self.detector = detector
        self.tracker = tracker
        self.frame_stride = frame_stride

        self.frames_seen = 0
        self.frames_analyzed = 0

        self.total_detections = 0
        self.total_inference_time_ms = 0.0

        self.detection_class_counts: dict[str, int] = {}

        self.unique_track_ids_by_class: dict[
            str,
            set[int],
        ] = {}

        self.maximum_concurrent_confirmed_tracks = 0
        self.removed_track_count = 0

    def start(
        self,
        context: VideoContext,
    ) -> None:
        """Reset detection and tracking state for a new video."""

        self.tracker.reset()

        self.frames_seen = 0
        self.frames_analyzed = 0

        self.total_detections = 0
        self.total_inference_time_ms = 0.0

        self.detection_class_counts = {}
        self.unique_track_ids_by_class = {}

        self.maximum_concurrent_confirmed_tracks = 0
        self.removed_track_count = 0

    def process_frame(
        self,
        packet: FramePacket,
    ) -> FrameAnalysis:
        """Detect and track objects on a sampled frame."""

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

        confirmed_tracks = tracking_result.confirmed_tracks

        detection_class_counts = detection_result.count_by_class()

        confirmed_track_counts = tracking_result.count_by_class()

        self.frames_analyzed += 1

        self.total_detections += detection_result.count

        self.total_inference_time_ms += detection_result.inference_time_ms

        self.removed_track_count += len(tracking_result.removed_track_ids)

        self.maximum_concurrent_confirmed_tracks = max(
            self.maximum_concurrent_confirmed_tracks,
            len(confirmed_tracks),
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
            class_track_ids = self.unique_track_ids_by_class.setdefault(
                track.class_name,
                set(),
            )

            class_track_ids.add(track.track_id)

        annotated_frame = annotate_tracks(
            packet.image,
            tracking_result.tracks,
        )

        unique_track_counts = self._unique_track_counts()

        return FrameAnalysis(
            analyzed=True,
            detections=detection_result.detections,
            tracks=tracking_result.tracks,
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
                "unique_track_counts": (unique_track_counts),
                "removed_track_ids": list(tracking_result.removed_track_ids),
            },
        )

    def finish(self) -> PipelineSummary:
        """Return video-level detection and tracking statistics."""

        average_inference_time_ms = 0.0

        if self.frames_analyzed > 0:
            average_inference_time_ms = (
                self.total_inference_time_ms / self.frames_analyzed
            )

        unique_track_counts = self._unique_track_counts()

        total_unique_confirmed_tracks = sum(unique_track_counts.values())

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
                "unique_confirmed_tracks": (total_unique_confirmed_tracks),
                "unique_track_counts_by_class": (unique_track_counts),
                "maximum_concurrent_confirmed_tracks": (
                    self.maximum_concurrent_confirmed_tracks
                ),
                "removed_track_count": (self.removed_track_count),
            }
        )

    def _unique_track_counts(
        self,
    ) -> dict[str, int]:
        """Count confirmed track identities by class."""

        return {
            class_name: len(track_ids)
            for class_name, track_ids in sorted(self.unique_track_ids_by_class.items())
        }
