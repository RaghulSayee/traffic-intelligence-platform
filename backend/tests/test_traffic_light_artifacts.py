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
from app.reasoning.traffic_light_state import (
    TrafficLightObservation,
    TrafficLightState,
)
from app.reasoning.traffic_light_temporal import (
    StableTrafficLightSnapshot,
    TrafficLightStateTransition,
)


def test_artifact_contains_traffic_light_state(
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

    observation = TrafficLightObservation(
        region_id="signal-1",
        region_name="Main Signal",
        state=TrafficLightState.RED,
        confidence=0.95,
        red_score=0.20,
        yellow_score=0.0,
        green_score=0.0,
        active_pixel_ratio=0.20,
        polygon_pixel_count=1000,
        active_pixel_count=200,
    )

    state = StableTrafficLightSnapshot(
        region_id="signal-1",
        region_name="Main Signal",
        raw_state=TrafficLightState.RED,
        raw_confidence=0.95,
        stable_state=TrafficLightState.RED,
        stable_confidence=0.92,
        candidate_state=(TrafficLightState.UNKNOWN),
        candidate_confidence=0.0,
        consecutive_candidate_frames=0,
        unknown_frames=0,
        red_score=0.20,
        yellow_score=0.0,
        green_score=0.0,
        active_pixel_ratio=0.20,
        last_observed_frame=3,
        observed_this_frame=True,
    )

    transition = TrafficLightStateTransition(
        region_id="signal-1",
        region_name="Main Signal",
        previous_state=(TrafficLightState.UNKNOWN),
        current_state=(TrafficLightState.RED),
        confidence=0.92,
        frame_number=3,
        timestamp_seconds=0.2,
        confirmation_frames=3,
    )

    packet = FramePacket(
        frame_number=3,
        timestamp_seconds=0.2,
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
        traffic_light_observations=(observation,),
        traffic_light_states=(state,),
        traffic_light_transitions=(transition,),
    )

    writer.write(
        packet=packet,
        analysis=analysis,
    )

    writer.finish(
        pipeline_summary={
            "pipeline_version": "0.9.0",
        }
    )

    path = tmp_path / str(job_id) / "detections.jsonl"

    record = json.loads(path.read_text(encoding="utf-8").splitlines()[0])

    assert record["schema_version"] == "1.7"

    traffic_lights = record["traffic_lights"]

    assert traffic_lights["observations"][0]["state"] == "red"

    assert traffic_lights["states"][0]["stable_state"] == "red"

    assert traffic_lights["transitions"][0]["previous_state"] == "unknown"

    assert traffic_lights["transitions"][0]["current_state"] == "red"
