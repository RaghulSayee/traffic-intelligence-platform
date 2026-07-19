from app.detection.annotation import annotate_detections
from app.detection.base import ObjectDetector
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
    PipelineSummary,
    VideoContext,
)


class YoloTrafficPipeline:
    """Run traffic-object detection on sampled video frames."""

    name = "yolo-traffic-pipeline"
    version = "0.2.0"

    def __init__(
        self,
        *,
        detector: ObjectDetector,
        frame_stride: int,
    ) -> None:
        if frame_stride <= 0:
            raise ValueError("Frame stride must be greater than zero.")

        self.detector = detector
        self.frame_stride = frame_stride

        self.frames_seen = 0
        self.frames_analyzed = 0
        self.total_detections = 0
        self.total_inference_time_ms = 0.0

        self.class_counts: dict[str, int] = {}

    def start(
        self,
        context: VideoContext,
    ) -> None:
        """Reset state before processing a new video."""

        self.frames_seen = 0
        self.frames_analyzed = 0
        self.total_detections = 0
        self.total_inference_time_ms = 0.0

        self.class_counts = {}

    def process_frame(
        self,
        packet: FramePacket,
    ) -> FrameAnalysis:
        """Analyze a sampled frame using YOLO."""

        self.frames_seen += 1

        should_analyze = (packet.frame_number - 1) % self.frame_stride == 0

        if not should_analyze:
            return FrameAnalysis(
                analyzed=False,
            )

        result = self.detector.predict(packet.image)

        annotated_frame = annotate_detections(
            packet.image,
            result.detections,
        )

        frame_class_counts = result.count_by_class()

        self.frames_analyzed += 1
        self.total_detections += result.count
        self.total_inference_time_ms += result.inference_time_ms

        for class_name, count in frame_class_counts.items():
            self.class_counts[class_name] = (
                self.class_counts.get(
                    class_name,
                    0,
                )
                + count
            )

        return FrameAnalysis(
            analyzed=True,
            detections=result.detections,
            annotated_frame=annotated_frame,
            metrics={
                "frame_number": packet.frame_number,
                "inference_time_ms": (result.inference_time_ms),
                "detection_count": result.count,
                "class_counts": frame_class_counts,
            },
        )

    def finish(self) -> PipelineSummary:
        """Return video-level detection statistics."""

        average_inference_time_ms = 0.0

        if self.frames_analyzed > 0:
            average_inference_time_ms = (
                self.total_inference_time_ms / self.frames_analyzed
            )

        return PipelineSummary(
            metrics={
                "pipeline_name": self.name,
                "pipeline_version": self.version,
                "detector_model": (self.detector.model_name),
                "detector_device": (self.detector.device),
                "frame_stride": self.frame_stride,
                "frames_seen": self.frames_seen,
                "frames_analyzed": (self.frames_analyzed),
                "total_detections": (self.total_detections),
                "class_counts": self.class_counts,
                "average_inference_time_ms": (average_inference_time_ms),
            }
        )
