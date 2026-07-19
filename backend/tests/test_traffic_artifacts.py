import json
from pathlib import Path
from uuid import uuid4
from app.tracking.types import TrackedObject
import numpy as np

from app.artifacts.traffic_video import (
    TrafficVideoArtifactWriter,
)
from app.detection.types import (
    BoundingBox,
    Detection,
)
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
)


def test_artifact_writer_creates_jsonl_and_evidence(
    tmp_path: Path,
) -> None:
    job_id = uuid4()

    writer = TrafficVideoArtifactWriter(
        root=tmp_path,
        job_id=job_id,
        preview_fps=10,
        evidence_min_confidence=0.50,
        evidence_cooldown_frames=0,
        max_evidence_frames=5,
        preview_enabled=False,
    )

    frame = np.zeros(
        (120, 160, 3),
        dtype=np.uint8,
    )

    detection = Detection(
        class_id=2,
        class_name="car",
        confidence=0.90,
        bounding_box=BoundingBox(
            x1=10,
            y1=20,
            x2=100,
            y2=90,
        ),
        model_name="test-model",
    )

    packet = FramePacket(
        frame_number=1,
        timestamp_seconds=0.1,
        image=frame,
    )

    track = TrackedObject(
        track_id=7,
        class_id=2,
        class_name="car",
        confidence=0.90,
        bounding_box=BoundingBox(
            x1=10,
            y1=20,
            x2=100,
            y2=90,
        ),
        age=3,
        hits=3,
        missed_frames=0,
        confirmed=True,
        velocity_x=15.0,
        velocity_y=2.0,
    )

    analysis = FrameAnalysis(
        analyzed=True,
        detections=(detection,),
        tracks=(track,),
        annotated_frame=frame,
        metrics={
            "inference_time_ms": 12.5,
            "detection_count": 1,
            "confirmed_track_count": 1,
        },
    )

    writer.write(
        packet=packet,
        analysis=analysis,
    )

    artifact_summary = writer.finish(
        pipeline_summary={
            "total_detections": 1,
        }
    )

    final_directory = tmp_path / str(job_id)

    detections_path = final_directory / "detections.jsonl"

    summary_path = final_directory / "summary.json"

    evidence_path = final_directory / "evidence" / "frame-000001.jpg"

    assert detections_path.exists()
    assert summary_path.exists()
    assert evidence_path.exists()

    detection_record = json.loads(detections_path.read_text(encoding="utf-8").strip())

    assert detection_record["frame_number"] == 1

    assert detection_record["detections"][0]["class_name"] == "car"

    assert detection_record["tracks"][0]["track_id"] == 7

    assert detection_record["tracks"][0]["confirmed"] is True

    assert artifact_summary.analyzed_frames == 1
    assert len(artifact_summary.evidence_keys) == 1
