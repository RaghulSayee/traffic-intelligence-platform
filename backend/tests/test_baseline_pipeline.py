import numpy as np

from app.pipelines.base import (
    FramePacket,
    VideoContext,
)
from app.pipelines.baseline import (
    BaselineTrafficPipeline,
)


def test_baseline_pipeline_detects_frame_motion() -> None:
    pipeline = BaselineTrafficPipeline(
        motion_threshold=10,
        active_motion_ratio=0.001,
    )

    pipeline.start(
        VideoContext(
            video_id="test-video",
            width=100,
            height=100,
            frames_per_second=10,
            expected_frame_count=2,
        )
    )

    first_frame = np.zeros(
        (100, 100, 3),
        dtype=np.uint8,
    )

    second_frame = first_frame.copy()

    second_frame[
        20:60,
        20:60,
    ] = 255

    first_result = pipeline.process_frame(
        FramePacket(
            frame_number=1,
            timestamp_seconds=0.1,
            image=first_frame,
        )
    )

    second_result = pipeline.process_frame(
        FramePacket(
            frame_number=2,
            timestamp_seconds=0.2,
            image=second_frame,
        )
    )

    summary = pipeline.finish()

    assert first_result.metrics["motion_ratio"] == 0.0
    assert second_result.metrics["motion_ratio"] > 0.0

    assert summary.metrics["processed_frames"] == 2
    assert summary.metrics["motion_frame_percentage"] > 0.0
