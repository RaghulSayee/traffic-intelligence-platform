import json
from uuid import uuid4

import numpy as np

from app.artifacts.traffic_video import (
    TrafficVideoArtifactWriter,
)
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
)
from app.reasoning.red_light import (
    RedLightCrossingObservation,
    RedLightTransitionType,
    RedLightViolationTransition,
)
from app.reasoning.traffic_light_state import (
    TrafficLightState,
)


def create_crossing() -> RedLightCrossingObservation:
    return RedLightCrossingObservation(
        track_id=7,
        class_name="car",
        stop_line_id="stop-1",
        lane_id="lane-1",
        traffic_light_region_id="signal-1",
        signal_state=TrafficLightState.RED,
        signal_confidence=0.95,
        previous_frame_number=9,
        frame_number=10,
        timestamp_seconds=0.90,
        previous_anchor_x_normalized=0.50,
        previous_anchor_y_normalized=0.40,
        anchor_x_normalized=0.50,
        anchor_y_normalized=0.60,
        previous_signed_distance_pixels=-10.0,
        signed_distance_pixels=10.0,
        crossing_depth_pixels=20.0,
        velocity_x=0.0,
        velocity_y=100.0,
        speed_pixels_per_second=100.0,
        direction_cosine=1.0,
        detection_confidence=0.90,
        rule_confidence=0.95,
        is_violation=True,
    )


def create_transition() -> RedLightViolationTransition:
    crossing = create_crossing()

    return RedLightViolationTransition(
        transition_type=(RedLightTransitionType.STARTED),
        track_id=crossing.track_id,
        class_name=crossing.class_name,
        stop_line_id=crossing.stop_line_id,
        lane_id=crossing.lane_id,
        traffic_light_region_id=(crossing.traffic_light_region_id),
        signal_state=crossing.signal_state,
        signal_confidence=(crossing.signal_confidence),
        previous_frame_number=(crossing.previous_frame_number),
        frame_number=crossing.frame_number,
        timestamp_seconds=(crossing.timestamp_seconds),
        previous_anchor_x_normalized=(crossing.previous_anchor_x_normalized),
        previous_anchor_y_normalized=(crossing.previous_anchor_y_normalized),
        anchor_x_normalized=(crossing.anchor_x_normalized),
        anchor_y_normalized=(crossing.anchor_y_normalized),
        previous_signed_distance_pixels=(crossing.previous_signed_distance_pixels),
        signed_distance_pixels=(crossing.signed_distance_pixels),
        crossing_depth_pixels=(crossing.crossing_depth_pixels),
        velocity_x=crossing.velocity_x,
        velocity_y=crossing.velocity_y,
        speed_pixels_per_second=(crossing.speed_pixels_per_second),
        direction_cosine=(crossing.direction_cosine),
        detection_confidence=(crossing.detection_confidence),
        rule_confidence=(crossing.rule_confidence),
    )


def test_artifact_contains_red_light_analysis(
    tmp_path,
) -> None:
    job_id = uuid4()

    writer = TrafficVideoArtifactWriter(
        root=tmp_path,
        job_id=job_id,
        preview_fps=10.0,
        evidence_min_confidence=0.65,
        evidence_cooldown_frames=30,
        max_evidence_frames=0,
        preview_enabled=False,
    )

    packet = FramePacket(
        frame_number=10,
        timestamp_seconds=0.90,
        image=np.zeros(
            (
                200,
                200,
                3,
            ),
            dtype=np.uint8,
        ),
    )

    analysis = FrameAnalysis(
        red_light_crossings=(create_crossing(),),
        red_light_transitions=(create_transition(),),
    )

    writer.write(
        packet=packet,
        analysis=analysis,
    )

    writer.finish(
        pipeline_summary={
            "pipeline_version": "1.0.0",
        }
    )

    path = tmp_path / str(job_id) / "detections.jsonl"

    record = json.loads(path.read_text(encoding="utf-8").splitlines()[0])

    assert record["schema_version"] == "1.7"

    red_light = record["red_light_analysis"]

    assert red_light["crossings"][0]["signal_state"] == "red"

    assert red_light["crossings"][0]["is_violation"] is True

    assert red_light["transitions"][0]["transition_type"] == "started"

    assert red_light["transitions"][0]["stop_line_id"] == "stop-1"
