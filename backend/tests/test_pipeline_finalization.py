from app.pipelines.yolo_traffic import (
    YoloTrafficPipeline,
)


class FakeFlushDetector:
    """Detector double that records finalization calls."""

    def __init__(
        self,
        transitions=(),
    ) -> None:
        self.transitions = transitions
        self.calls = []

    def flush(
        self,
        *,
        frame_number: int,
        timestamp_seconds: float,
    ):
        self.calls.append(
            {
                "frame_number": frame_number,
                "timestamp_seconds": (timestamp_seconds),
            }
        )

        return self.transitions


def create_pipeline(
    *,
    triple_riding_transitions=(),
    no_helmet_transitions=(),
    wrong_way_transitions=(),
    lane_violation_transitions=(),
):
    pipeline = object.__new__(YoloTrafficPipeline)

    pipeline.last_frame_number = 120

    pipeline.last_timestamp_seconds = 11.9

    pipeline.triple_riding_detector = FakeFlushDetector(triple_riding_transitions)

    pipeline.no_helmet_detector = FakeFlushDetector(no_helmet_transitions)

    pipeline.wrong_way_detector = FakeFlushDetector(wrong_way_transitions)

    pipeline.lane_violation_detector = FakeFlushDetector(lane_violation_transitions)

    return pipeline


def test_collects_all_final_transitions() -> None:
    triple_riding = object()
    no_helmet = object()
    wrong_way = object()
    lane_violation = object()

    pipeline = create_pipeline(
        triple_riding_transitions=(triple_riding,),
        no_helmet_transitions=(no_helmet,),
        wrong_way_transitions=(wrong_way,),
        lane_violation_transitions=(lane_violation,),
    )

    result = pipeline._finalize_active_violations()

    assert result is not None

    assert result.triple_riding_transitions == (triple_riding,)

    assert result.no_helmet_transitions == (no_helmet,)

    assert result.wrong_way_transitions == (wrong_way,)

    assert result.lane_violation_transitions == (lane_violation,)

    assert result.analyzed is False

    detectors = (
        pipeline.triple_riding_detector,
        pipeline.no_helmet_detector,
        pipeline.wrong_way_detector,
        pipeline.lane_violation_detector,
    )

    for detector in detectors:
        assert detector.calls == [
            {
                "frame_number": 120,
                "timestamp_seconds": 11.9,
            }
        ]


def test_returns_none_when_no_states_are_active() -> None:
    pipeline = create_pipeline()

    result = pipeline._finalize_active_violations()

    assert result is None


def test_returns_none_before_any_frame() -> None:
    pipeline = create_pipeline(triple_riding_transitions=(object(),))

    pipeline.last_frame_number = None
    pipeline.last_timestamp_seconds = None

    result = pipeline._finalize_active_violations()

    assert result is None

    assert pipeline.triple_riding_detector.calls == []


def test_uses_actual_last_decoded_frame() -> None:
    pipeline = create_pipeline(wrong_way_transitions=(object(),))

    pipeline.last_frame_number = 137
    pipeline.last_timestamp_seconds = 13.64

    result = pipeline._finalize_active_violations()

    assert result is not None

    assert pipeline.wrong_way_detector.calls == [
        {
            "frame_number": 137,
            "timestamp_seconds": 13.64,
        }
    ]
