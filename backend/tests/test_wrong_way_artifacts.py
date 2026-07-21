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
from app.reasoning.wrong_way import (
    WrongWayTransition,
    WrongWayTransitionType,
    WrongWayViolationSnapshot,
)


def test_artifact_contains_wrong_way_analysis(
    tmp_path,
) -> None:
    job_id = uuid4()

    writer = TrafficVideoArtifactWriter(
        root=tmp_path,
        job_id=job_id,
        preview_fps=10.0,
        evidence_min_confidence=0.5,
        evidence_cooldown_frames=10,
        max_evidence_frames=0,
        preview_enabled=False,
    )

    state = WrongWayViolationSnapshot(
        track_id=9,
        class_name="car",
        lane_id="northbound",
        velocity_x=0.0,
        velocity_y=80.0,
        speed_pixels_per_second=80.0,
        cosine_similarity=-1.0,
        opposition_score=1.0,
        first_candidate_frame=1,
        confirmed_frame=3,
        last_violation_frame=3,
        consecutive_violation_frames=3,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )

    transition = WrongWayTransition(
        transition_type=(WrongWayTransitionType.STARTED),
        track_id=9,
        class_name="car",
        lane_id="northbound",
        velocity_x=0.0,
        velocity_y=80.0,
        speed_pixels_per_second=80.0,
        cosine_similarity=-1.0,
        opposition_score=1.0,
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

    writer.write(
        packet=packet,
        analysis=FrameAnalysis(
            wrong_way_states=(state,),
            wrong_way_transitions=(transition,),
        ),
    )

    writer.finish(
        pipeline_summary={
            "pipeline_version": "1.0.0",
        }
    )

    detections_path = tmp_path / str(job_id) / "detections.jsonl"

    record = json.loads(detections_path.read_text(encoding="utf-8").splitlines()[0])

    assert record["schema_version"] == "1.7"

    wrong_way = record["road_rules"]["wrong_way"]

    assert len(wrong_way["states"]) == 1
    assert len(wrong_way["transitions"]) == 1

    assert wrong_way["states"][0]["lane_id"] == "northbound"

    assert wrong_way["transitions"][0]["type"] == "started"
