import numpy as np

from app.detection.types import (
    BoundingBox,
    Detection,
    DetectionResult,
)
from app.pipelines.base import (
    FramePacket,
    VideoContext,
)
from app.pipelines.yolo_traffic import (
    YoloTrafficPipeline,
)
from app.tracking.multi_object import (
    MultiObjectTracker,
)


class FakeDetector:
    """Detector used without loading real model weights."""

    model_name = "fake-traffic-model"
    device = "cpu"

    def __init__(self) -> None:
        self.calls = 0

    def predict(
        self,
        frame,
    ) -> DetectionResult:
        self.calls += 1

        return DetectionResult(
            detections=(
                Detection(
                    class_id=3,
                    class_name="motorcycle",
                    confidence=0.90,
                    bounding_box=BoundingBox(
                        x1=10,
                        y1=20,
                        x2=100,
                        y2=150,
                    ),
                    model_name=self.model_name,
                ),
            ),
            inference_time_ms=12.5,
            image_width=frame.shape[1],
            image_height=frame.shape[0],
        )


def create_tracker() -> MultiObjectTracker:
    return MultiObjectTracker(
        high_confidence_threshold=0.60,
        low_confidence_threshold=0.35,
        primary_iou_threshold=0.30,
        secondary_iou_threshold=0.15,
        minimum_confirmed_hits=1,
        maximum_missed_frames=2,
        process_noise=1.0,
        measurement_noise=10.0,
    )


def test_yolo_pipeline_tracks_sampled_frames() -> None:
    detector = FakeDetector()

    pipeline = YoloTrafficPipeline(
        detector=detector,
        tracker=create_tracker(),
        frame_stride=2,
    )

    pipeline.start(
        VideoContext(
            video_id="test-video",
            width=320,
            height=240,
            frames_per_second=30,
            expected_frame_count=3,
        )
    )

    frame = np.zeros(
        (240, 320, 3),
        dtype=np.uint8,
    )

    first = pipeline.process_frame(
        FramePacket(
            frame_number=1,
            timestamp_seconds=0.0,
            image=frame,
        )
    )

    second = pipeline.process_frame(
        FramePacket(
            frame_number=2,
            timestamp_seconds=0.03,
            image=frame,
        )
    )

    third = pipeline.process_frame(
        FramePacket(
            frame_number=3,
            timestamp_seconds=0.06,
            image=frame,
        )
    )

    summary = pipeline.finish()

    assert first.analyzed is True
    assert second.analyzed is False
    assert third.analyzed is True

    assert detector.calls == 2

    assert len(first.tracks) == 1
    assert len(third.tracks) == 1

    assert first.tracks[0].track_id == third.tracks[0].track_id

    assert summary.metrics["frames_seen"] == 3
    assert summary.metrics["frames_analyzed"] == 2

    assert summary.metrics["total_detection_occurrences"] == 2

    assert summary.metrics["unique_confirmed_tracks"] == 1

    assert summary.metrics["unique_track_counts_by_class"] == {
        "motorcycle": 1,
    }
