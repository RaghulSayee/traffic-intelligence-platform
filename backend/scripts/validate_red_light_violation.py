from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import cv2
import numpy as np

from app.artifacts.traffic_video import (
    TrafficVideoArtifactWriter,
)
from app.detection.types import BoundingBox
from app.models.violation_event import ViolationEvent
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
)
from app.pipelines.yolo_traffic import (
    YoloTrafficPipeline,
)
from app.reasoning.red_light import (
    RedLightCrossingDetector,
    RedLightViolationTransition,
)
from app.reasoning.red_light_annotation import (
    annotate_red_light_crossings,
)
from app.reasoning.traffic_light_annotation import (
    annotate_traffic_light_states,
)
from app.reasoning.traffic_light_state import (
    TrafficLightStateClassifier,
)
from app.reasoning.traffic_light_temporal import (
    TrafficLightTemporalStabilizer,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)
from app.services.violation_event_lifecycle import (
    ViolationEventLifecycleService,
)
from app.tracking.types import TrackedObject


FRAME_WIDTH = 320
FRAME_HEIGHT = 240
FRAMES_PER_SECOND = 10.0

OUTPUT_ROOT = Path("storage/validation/red-light-violation")

ANCHOR_Y_POSITIONS = (
    90.0,
    96.0,
    102.0,
    108.0,
    132.0,
    150.0,
    168.0,
    185.0,
)


class FakeViolationEventRepository:
    """Isolated event repository for validation."""

    def __init__(self) -> None:
        self.events_by_key: dict[
            str,
            ViolationEvent,
        ] = {}

        self.commit_count = 0

    async def get_by_event_key(
        self,
        event_key: str,
        *,
        for_update: bool = False,
    ) -> ViolationEvent | None:
        del for_update

        return self.events_by_key.get(event_key)

    async def create(
        self,
        event: ViolationEvent,
    ) -> ViolationEvent:
        self.events_by_key[event.event_key] = event

        return event

    async def list_by_processing_job(
        self,
        processing_job_id: UUID,
        *,
        for_update: bool = False,
    ) -> list[ViolationEvent]:
        del for_update

        return [
            event
            for event in self.events_by_key.values()
            if event.processing_job_id == processing_job_id
        ]

    async def commit(self) -> None:
        self.commit_count += 1


def create_scene() -> CameraSceneConfiguration:
    """Create one lane, signal region, and stop line."""

    return CameraSceneConfiguration(
        enabled_violations=[
            "red_light",
        ],
        lanes=[
            {
                "lane_id": "validation-lane",
                "name": "Southbound Validation Lane",
                "polygon": {
                    "points": [
                        {
                            "x": 0.10,
                            "y": 0.20,
                        },
                        {
                            "x": 0.90,
                            "y": 0.20,
                        },
                        {
                            "x": 0.90,
                            "y": 0.95,
                        },
                        {
                            "x": 0.10,
                            "y": 0.95,
                        },
                    ]
                },
                "allowed_direction": {
                    "x": 0.0,
                    "y": 1.0,
                },
            }
        ],
        traffic_light_regions=[
            {
                "region_id": "validation-signal",
                "name": "Validation Signal",
                "polygon": {
                    "points": [
                        {
                            "x": 0.05,
                            "y": 0.05,
                        },
                        {
                            "x": 0.22,
                            "y": 0.05,
                        },
                        {
                            "x": 0.22,
                            "y": 0.35,
                        },
                        {
                            "x": 0.05,
                            "y": 0.35,
                        },
                    ]
                },
            }
        ],
        stop_lines=[
            {
                "stop_line_id": "validation-stop-line",
                "lane_id": "validation-lane",
                "traffic_light_region_id": ("validation-signal"),
                "line": {
                    "start": {
                        "x": 0.20,
                        "y": 0.50,
                    },
                    "end": {
                        "x": 0.80,
                        "y": 0.50,
                    },
                },
            }
        ],
    )


def create_frame(
    *,
    frame_number: int,
    anchor_y: float,
) -> np.ndarray:
    """Create one synthetic road frame with a red signal."""

    frame = np.full(
        (
            FRAME_HEIGHT,
            FRAME_WIDTH,
            3,
        ),
        35,
        dtype=np.uint8,
    )

    # Road.
    cv2.rectangle(
        frame,
        (
            35,
            55,
        ),
        (
            285,
            239,
        ),
        (
            65,
            65,
            65,
        ),
        thickness=-1,
    )

    # Lane boundaries.
    cv2.line(
        frame,
        (
            70,
            55,
        ),
        (
            70,
            239,
        ),
        (
            180,
            180,
            180,
        ),
        2,
    )

    cv2.line(
        frame,
        (
            250,
            55,
        ),
        (
            250,
            239,
        ),
        (
            180,
            180,
            180,
        ),
        2,
    )

    # Stop line.
    cv2.line(
        frame,
        (
            64,
            120,
        ),
        (
            256,
            120,
        ),
        (
            240,
            240,
            240,
        ),
        4,
    )

    # Traffic-light housing.
    cv2.rectangle(
        frame,
        (
            24,
            18,
        ),
        (
            62,
            78,
        ),
        (
            5,
            5,
            5,
        ),
        thickness=-1,
    )

    # Active red lamp.
    cv2.circle(
        frame,
        (
            43,
            40,
        ),
        14,
        (
            0,
            0,
            255,
        ),
        thickness=-1,
        lineType=cv2.LINE_AA,
    )

    # Synthetic vehicle.
    box_width = 40
    box_height = 30

    x1 = round(FRAME_WIDTH / 2 - box_width / 2)

    y1 = round(anchor_y - box_height * 0.90)

    cv2.rectangle(
        frame,
        (
            x1,
            y1,
        ),
        (
            x1 + box_width,
            y1 + box_height,
        ),
        (
            255,
            120,
            40,
        ),
        thickness=-1,
    )

    cv2.putText(
        frame,
        f"Frame {frame_number}",
        (
            210,
            25,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (
            230,
            230,
            230,
        ),
        1,
        cv2.LINE_AA,
    )

    return frame


def create_track(
    *,
    frame_number: int,
    anchor_y: float,
) -> TrackedObject:
    """Create one confirmed southbound car track."""

    box_width = 40.0
    box_height = 30.0

    center_x = FRAME_WIDTH / 2

    y1 = anchor_y - box_height * 0.90

    return TrackedObject(
        track_id=42,
        class_id=2,
        class_name="car",
        confidence=0.93,
        bounding_box=BoundingBox(
            x1=(center_x - box_width / 2.0),
            y1=y1,
            x2=(center_x + box_width / 2.0),
            y2=y1 + box_height,
        ),
        age=frame_number,
        hits=frame_number,
        missed_frames=0,
        confirmed=True,
        velocity_x=0.0,
        velocity_y=100.0,
    )


def replace_latest_link(
    *,
    output_root: Path,
    job_id: UUID,
) -> Path:
    """Create a latest symlink for local inspection."""

    latest = output_root / "latest"

    if latest.is_symlink():
        latest.unlink()

    elif latest.exists():
        raise RuntimeError(f"Cannot replace an existing non-symlink path: {latest}")

    latest.symlink_to(
        str(job_id),
        target_is_directory=True,
    )

    return latest


async def main() -> None:
    assert YoloTrafficPipeline.version == "1.0.0"

    scene = create_scene()

    classifier = TrafficLightStateClassifier(
        minimum_saturation=80,
        minimum_value=100,
        minimum_active_pixel_ratio=0.01,
        dominance_ratio=1.25,
    )

    stabilizer = TrafficLightTemporalStabilizer(
        confirmation_frames=3,
        maximum_unknown_frames=2,
        confidence_alpha=0.40,
    )

    red_light_detector = RedLightCrossingDetector(
        minimum_speed_pixels_per_second=10.0,
        minimum_direction_cosine=0.25,
        line_crossing_tolerance_pixels=3.0,
        minimum_signal_confidence=0.60,
        maximum_missed_frames=2,
    )

    repository = FakeViolationEventRepository()

    lifecycle = ViolationEventLifecycleService(repository=repository)

    job_id = uuid4()
    video_id = uuid4()
    camera_id = uuid4()

    video_created_at = datetime(
        2026,
        7,
        21,
        12,
        0,
        tzinfo=timezone.utc,
    )

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    writer = TrafficVideoArtifactWriter(
        root=OUTPUT_ROOT,
        job_id=job_id,
        preview_fps=FRAMES_PER_SECOND,
        evidence_min_confidence=0.99,
        evidence_cooldown_frames=100,
        max_evidence_frames=3,
        preview_enabled=True,
    )

    emitted_transitions: list[RedLightViolationTransition] = []

    try:
        for frame_number, anchor_y in enumerate(
            ANCHOR_Y_POSITIONS,
            start=1,
        ):
            timestamp_seconds = (frame_number - 1) / FRAMES_PER_SECOND

            frame = create_frame(
                frame_number=frame_number,
                anchor_y=anchor_y,
            )

            track = create_track(
                frame_number=frame_number,
                anchor_y=anchor_y,
            )

            raw_signal_result = classifier.classify(
                frame=frame,
                scene=scene,
            )

            stable_signal_result = stabilizer.update(
                frame_number=frame_number,
                timestamp_seconds=(timestamp_seconds),
                observations=(raw_signal_result),
            )

            red_light_result = red_light_detector.update(
                frame_number=frame_number,
                timestamp_seconds=(timestamp_seconds),
                tracks=(track,),
                traffic_light_states=(stable_signal_result.states),
                scene=scene,
                image_width=FRAME_WIDTH,
                image_height=FRAME_HEIGHT,
            )

            annotated = annotate_traffic_light_states(
                frame,
                scene=scene,
                states=(stable_signal_result.states),
            )

            annotated = annotate_red_light_crossings(
                annotated,
                scene=scene,
                crossings=(red_light_result.observations),
            )

            analysis = FrameAnalysis(
                tracks=(track,),
                red_light_crossings=(red_light_result.observations),
                red_light_transitions=(red_light_result.transitions),
                traffic_light_observations=(raw_signal_result.observations),
                traffic_light_states=(stable_signal_result.states),
                traffic_light_transitions=(stable_signal_result.transitions),
                annotated_frame=annotated,
                metrics={
                    "frame_number": (frame_number),
                    "red_light_crossing_count": len(red_light_result.observations),
                    "red_light_violation_count": len(red_light_result.transitions),
                },
            )

            packet = FramePacket(
                frame_number=frame_number,
                timestamp_seconds=(timestamp_seconds),
                image=frame,
            )

            writer.write(
                packet=packet,
                analysis=analysis,
            )

            if red_light_result.transitions:
                emitted_transitions.extend(red_light_result.transitions)

                await lifecycle.persist_red_light_transitions(
                    processing_job_id=job_id,
                    video_id=video_id,
                    camera_id=camera_id,
                    video_created_at=(video_created_at),
                    transitions=(red_light_result.transitions),
                )

        artifact_summary = writer.finish(
            pipeline_summary={
                "pipeline_name": ("yolo-traffic-pipeline"),
                "pipeline_version": "1.0.0",
                "artifact_schema_version": "1.7",
                "validation_type": ("synthetic-red-light-violation"),
                "processed_frames": len(ANCHOR_Y_POSITIONS),
                "red_light_violation_count": len(emitted_transitions),
            }
        )

    except Exception:
        writer.abort()
        raise

    assert len(emitted_transitions) == 1
    assert len(repository.events_by_key) == 1

    transition = emitted_transitions[0]

    assert transition.track_id == 42

    assert transition.stop_line_id == "validation-stop-line"

    assert transition.signal_state.value == "red"

    assert artifact_summary.preview_key is not None
    assert len(artifact_summary.evidence_keys) == 1

    await lifecycle.attach_preview_to_job_events(
        processing_job_id=job_id,
        preview_key=(artifact_summary.preview_key),
    )

    await lifecycle.attach_images_to_job_events(
        processing_job_id=job_id,
        evidence_keys=(artifact_summary.evidence_keys),
    )

    # Replay the same transition.
    await lifecycle.persist_red_light_transitions(
        processing_job_id=job_id,
        video_id=video_id,
        camera_id=camera_id,
        video_created_at=(video_created_at),
        transitions=(transition,),
    )

    assert len(repository.events_by_key) == 1

    event = next(iter(repository.events_by_key.values()))

    assert event.evidence_image_key == artifact_summary.evidence_keys[0]

    assert event.evidence_clip_key == artifact_summary.preview_key

    assert len(event.event_metadata["transition_history"]) == 1

    job_directory = OUTPUT_ROOT / str(job_id)

    detections_path = job_directory / "detections.jsonl"

    records = [
        json.loads(line)
        for line in detections_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    artifact_transition_count = sum(
        len(record["red_light_analysis"]["transitions"]) for record in records
    )

    assert artifact_transition_count == 1

    summary = {
        "validation_status": "passed",
        "pipeline_version": "1.0.0",
        "artifact_schema_version": "1.7",
        "job_id": str(job_id),
        "video_id": str(video_id),
        "camera_id": str(camera_id),
        "processed_frames": len(ANCHOR_Y_POSITIONS),
        "transition_frame": (transition.frame_number),
        "track_id": transition.track_id,
        "stop_line_id": (transition.stop_line_id),
        "signal_state": (transition.signal_state.value),
        "signal_confidence": (transition.signal_confidence),
        "rule_confidence": (transition.rule_confidence),
        "event_key": event.event_key,
        "event_count_after_replay": len(repository.events_by_key),
        "transition_history_count": len(event.event_metadata["transition_history"]),
        "evidence_image_key": (event.evidence_image_key),
        "preview_key": (event.evidence_clip_key),
        "detections_key": (artifact_summary.detections_key),
        "artifact_transition_count": (artifact_transition_count),
        "repository_commit_count": (repository.commit_count),
    }

    summary_path = job_directory / "validation_summary.json"

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    latest = replace_latest_link(
        output_root=OUTPUT_ROOT,
        job_id=job_id,
    )

    print()
    print("Red-light violation validation passed.")

    print(
        "Pipeline version:",
        "1.0.0",
    )

    print(
        "Artifact schema:",
        "1.7",
    )

    print(
        "Transition frame:",
        transition.frame_number,
    )

    print(
        "Event key:",
        event.event_key,
    )

    print(
        "Evidence:",
        event.evidence_image_key,
    )

    print(
        "Preview:",
        event.evidence_clip_key,
    )

    print(
        "Events after replay:",
        len(repository.events_by_key),
    )

    print(
        "Validation directory:",
        latest,
    )


if __name__ == "__main__":
    asyncio.run(main())
