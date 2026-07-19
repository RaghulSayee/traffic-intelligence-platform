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
from app.reasoning.rider_motorcycle import (
    RiderMotorcycleAssociator,
)
from app.reasoning.temporal_rider import (
    TemporalRiderAssociationSmoother,
)
from app.reasoning.triple_riding import (
    TripleRidingViolationDetector,
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


class TripleRidingFakeDetector:
    model_name = "fake-triple-riding-model"
    device = "cpu"

    def predict(
        self,
        frame,
    ) -> DetectionResult:
        detections = (
            Detection(
                class_id=0,
                class_name="person",
                confidence=0.95,
                bounding_box=BoundingBox(
                    x1=90,
                    y1=40,
                    x2=145,
                    y2=190,
                ),
                model_name=self.model_name,
            ),
            Detection(
                class_id=0,
                class_name="person",
                confidence=0.94,
                bounding_box=BoundingBox(
                    x1=125,
                    y1=40,
                    x2=180,
                    y2=190,
                ),
                model_name=self.model_name,
            ),
            Detection(
                class_id=0,
                class_name="person",
                confidence=0.93,
                bounding_box=BoundingBox(
                    x1=160,
                    y1=40,
                    x2=215,
                    y2=190,
                ),
                model_name=self.model_name,
            ),
            Detection(
                class_id=3,
                class_name="motorcycle",
                confidence=0.96,
                bounding_box=BoundingBox(
                    x1=80,
                    y1=160,
                    x2=225,
                    y2=265,
                ),
                model_name=self.model_name,
            ),
        )

        return DetectionResult(
            detections=detections,
            inference_time_ms=10.0,
            image_width=frame.shape[1],
            image_height=frame.shape[0],
        )


def test_pipeline_confirms_triple_riding() -> None:
    pipeline = create_reasoning_pipeline(
        detector=TripleRidingFakeDetector(),
        temporal_confirmation_frames=2,
        violation_confirmation_frames=2,
    )

    pipeline.start(
        VideoContext(
            video_id="triple-riding-video",
            width=320,
            height=280,
            frames_per_second=30,
            expected_frame_count=3,
        )
    )

    frame = np.zeros(
        (280, 320, 3),
        dtype=np.uint8,
    )

    results = []

    for frame_number in range(1, 4):
        results.append(
            pipeline.process_frame(
                FramePacket(
                    frame_number=frame_number,
                    timestamp_seconds=((frame_number - 1) / 30),
                    image=frame,
                )
            )
        )

    summary = pipeline.finish()

    assert results[0].triple_riding_states == ()

    assert len(results[2].triple_riding_states) == 1

    violation = results[2].triple_riding_states[0]

    assert violation.confirmed is True
    assert violation.rider_count == 3

    assert len(results[2].triple_riding_transitions) == 1

    assert summary.metrics["triple_riding_event_count"] == 1

    assert summary.metrics["maximum_riders_on_motorcycle"] == 3


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

    pipeline = create_reasoning_pipeline(
        detector=detector,
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


def create_reasoning_pipeline(
    *,
    detector,
    frame_stride: int = 1,
    temporal_confirmation_frames: int = 1,
    violation_confirmation_frames: int = 1,
) -> YoloTrafficPipeline:
    return YoloTrafficPipeline(
        detector=detector,
        tracker=create_tracker(),
        rider_associator=(
            RiderMotorcycleAssociator(
                minimum_score=0.55,
                max_riders_per_motorcycle=3,
                max_anchor_distance_ratio=2.0,
                minimum_horizontal_overlap=0.05,
                minimum_motion_speed=5.0,
            )
        ),
        rider_smoother=(
            TemporalRiderAssociationSmoother(
                confirmation_frames=(temporal_confirmation_frames),
                maximum_missed_frames=2,
                score_alpha=0.40,
            )
        ),
        triple_riding_detector=(
            TripleRidingViolationDetector(
                minimum_riders=3,
                confirmation_frames=(violation_confirmation_frames),
                maximum_missed_frames=2,
            )
        ),
        frame_stride=frame_stride,
    )
