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
from app.reasoning.lane_occupancy import (
    LaneOccupancyObservation,
)
from app.reasoning.lane_violation import (
    LaneViolationSnapshot,
    LaneViolationTransition,
    LaneViolationTransitionType,
)


def test_artifact_contains_lane_analysis(
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

    observation = LaneOccupancyObservation(
        track_id=7,
        class_name="car",
        lane_id=None,
        nearest_lane_id="lane-1",
        anchor_x_normalized=0.75,
        anchor_y_normalized=0.60,
        distance_to_nearest_lane_pixels=50.0,
        velocity_x=80.0,
        velocity_y=0.0,
        speed_pixels_per_second=80.0,
        inside_monitoring_zone=True,
        outside_configured_lanes=True,
        within_boundary_tolerance=False,
        violation_candidate=True,
    )

    state = LaneViolationSnapshot(
        track_id=7,
        class_name="car",
        nearest_lane_id="lane-1",
        anchor_x_normalized=0.75,
        anchor_y_normalized=0.60,
        distance_to_nearest_lane_pixels=50.0,
        velocity_x=80.0,
        velocity_y=0.0,
        speed_pixels_per_second=80.0,
        first_candidate_frame=1,
        confirmed_frame=3,
        last_violation_frame=3,
        consecutive_violation_frames=3,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )

    transition = LaneViolationTransition(
        transition_type=(LaneViolationTransitionType.STARTED),
        track_id=7,
        class_name="car",
        nearest_lane_id="lane-1",
        anchor_x_normalized=0.75,
        anchor_y_normalized=0.60,
        distance_to_nearest_lane_pixels=50.0,
        velocity_x=80.0,
        velocity_y=0.0,
        speed_pixels_per_second=80.0,
        frame_number=3,
        timestamp_seconds=0.2,
        first_candidate_frame=1,
        confirmed_frame=3,
        duration_seconds=0.0,
    )

    packet = FramePacket(
        frame_number=3,
        timestamp_seconds=0.2,
        image=np.zeros(
            (
                360,
                640,
                3,
            ),
            dtype=np.uint8,
        ),
    )

    analysis = FrameAnalysis(
        lane_occupancy_observations=(observation,),
        lane_violation_states=(state,),
        lane_violation_transitions=(transition,),
    )

    writer.write(
        packet=packet,
        analysis=analysis,
    )

    writer.finish(
        pipeline_summary={
            "pipeline_version": "0.7.0",
        }
    )

    artifact_path = tmp_path / str(job_id) / "detections.jsonl"

    record = json.loads(artifact_path.read_text(encoding="utf-8").splitlines()[0])

    assert record["schema_version"] == "1.5"

    lane_analysis = record["lane_analysis"]

    assert lane_analysis["occupancy"][0]["track_id"] == 7

    assert lane_analysis["occupancy"][0]["violation_candidate"] is True

    assert lane_analysis["violations"]["states"][0]["confirmed"] is True

    assert lane_analysis["violations"]["transitions"][0]["transition_type"] == "started"
