from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from uuid import UUID, uuid4

import cv2
import numpy as np

from app.artifacts.traffic_video import (
    TrafficVideoArtifactWriter,
)
from app.core.config import get_settings
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
)
from app.pipelines.factory import (
    VideoPipelineFactory,
)
from app.pipelines.yolo_traffic import (
    YoloTrafficPipeline,
)
from app.reasoning.traffic_light_annotation import (
    annotate_traffic_light_states,
)
from app.reasoning.traffic_light_state import (
    TrafficLightState,
    TrafficLightStateClassifier,
)
from app.reasoning.traffic_light_temporal import (
    TrafficLightTemporalStabilizer,
)
from app.schemas.camera_scene import (
    CameraSceneConfiguration,
)


FRAME_WIDTH = 640
FRAME_HEIGHT = 360
FRAMES_PER_SECOND = 10.0

OUTPUT_ROOT = Path("storage/validation/traffic-light-state")

PHASES: tuple[
    tuple[
        TrafficLightState,
        int,
    ],
    ...,
] = (
    (
        TrafficLightState.RED,
        15,
    ),
    (
        TrafficLightState.YELLOW,
        15,
    ),
    (
        TrafficLightState.GREEN,
        15,
    ),
    (
        TrafficLightState.UNKNOWN,
        5,
    ),
    (
        TrafficLightState.RED,
        15,
    ),
)

BGR_COLORS = {
    TrafficLightState.RED: (
        0,
        0,
        255,
    ),
    TrafficLightState.YELLOW: (
        0,
        255,
        255,
    ),
    TrafficLightState.GREEN: (
        0,
        255,
        0,
    ),
}


def create_scene() -> CameraSceneConfiguration:
    """Create a scene with one tightly configured signal region."""

    return CameraSceneConfiguration(
        enabled_violations=[
            "red_light",
        ],
        traffic_light_regions=[
            {
                "region_id": "synthetic-signal-1",
                "name": "Synthetic Main Signal",
                "polygon": {
                    "points": [
                        {
                            "x": 0.10,
                            "y": 0.08,
                        },
                        {
                            "x": 0.32,
                            "y": 0.08,
                        },
                        {
                            "x": 0.32,
                            "y": 0.62,
                        },
                        {
                            "x": 0.10,
                            "y": 0.62,
                        },
                    ]
                },
            }
        ],
    )


def create_synthetic_frame(
    *,
    state: TrafficLightState,
    frame_number: int,
) -> np.ndarray:
    """Create one synthetic traffic-light video frame."""

    frame = np.full(
        (
            FRAME_HEIGHT,
            FRAME_WIDTH,
            3,
        ),
        42,
        dtype=np.uint8,
    )

    # Background road.
    cv2.rectangle(
        frame,
        (
            0,
            245,
        ),
        (
            FRAME_WIDTH,
            FRAME_HEIGHT,
        ),
        (
            65,
            65,
            65,
        ),
        thickness=-1,
    )

    cv2.line(
        frame,
        (
            0,
            305,
        ),
        (
            FRAME_WIDTH,
            305,
        ),
        (
            220,
            220,
            220,
        ),
        thickness=3,
    )

    # Signal housing. This remains inside the configured region.
    housing_left = 82
    housing_top = 38
    housing_right = 184
    housing_bottom = 210

    cv2.rectangle(
        frame,
        (
            housing_left,
            housing_top,
        ),
        (
            housing_right,
            housing_bottom,
        ),
        (
            10,
            10,
            10,
        ),
        thickness=-1,
    )

    light_centers = {
        TrafficLightState.RED: (
            133,
            76,
        ),
        TrafficLightState.YELLOW: (
            133,
            124,
        ),
        TrafficLightState.GREEN: (
            133,
            172,
        ),
    }

    for light_state, center in light_centers.items():
        color = (
            BGR_COLORS[light_state]
            if state == light_state
            else (
                25,
                25,
                25,
            )
        )

        cv2.circle(
            frame,
            center,
            22,
            color,
            thickness=-1,
            lineType=cv2.LINE_AA,
        )

    phase_label = state.value.upper()

    cv2.putText(
        frame,
        (f"Synthetic Traffic-Light Validation | {phase_label}"),
        (
            230,
            75,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (
            240,
            240,
            240,
        ),
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        f"Frame {frame_number}",
        (
            230,
            110,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (
            200,
            200,
            200,
        ),
        1,
        cv2.LINE_AA,
    )

    return frame


def create_video_writer(
    path: Path,
) -> cv2.VideoWriter:
    """Create an MP4 writer and verify that it opened."""

    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        FRAMES_PER_SECOND,
        (
            FRAME_WIDTH,
            FRAME_HEIGHT,
        ),
    )

    if not writer.isOpened():
        raise RuntimeError(f"Could not create video writer: {path}")

    return writer


def read_jsonl(
    path: Path,
) -> list[dict]:
    """Read all non-empty JSONL records."""

    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def find_preview(
    job_directory: Path,
) -> Path:
    """Locate the annotated preview produced by the artifact writer."""

    video_suffixes = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
    }

    candidates = sorted(
        path
        for path in job_directory.rglob("*")
        if (path.is_file() and path.suffix.lower() in video_suffixes)
    )

    if not candidates:
        raise AssertionError("No annotated preview was generated.")

    preview_named = [path for path in candidates if "preview" in path.name.lower()]

    return preview_named[0] if preview_named else candidates[0]


def verify_preview(
    preview_path: Path,
) -> int:
    """Verify that the generated preview can be decoded."""

    capture = cv2.VideoCapture(str(preview_path))

    if not capture.isOpened():
        raise AssertionError(f"Generated preview could not be opened: {preview_path}")

    decoded_frames = 0

    while True:
        success, _ = capture.read()

        if not success:
            break

        decoded_frames += 1

    capture.release()

    if decoded_frames == 0:
        raise AssertionError("Generated preview contained no frames.")

    return decoded_frames


def replace_latest_link(
    *,
    output_root: Path,
    job_id: UUID,
) -> Path:
    """Create a convenient latest symlink for inspection."""

    latest = output_root / "latest"

    if latest.is_symlink() or latest.exists():
        if latest.is_dir() and not latest.is_symlink():
            raise RuntimeError(f"Cannot replace real directory: {latest}")

        latest.unlink()

    latest.symlink_to(
        str(job_id),
        target_is_directory=True,
    )

    return latest


def main() -> None:
    settings = get_settings()

    runtime_pipeline = VideoPipelineFactory(settings).create("yolo-traffic-pipeline")

    assert YoloTrafficPipeline.version == "0.9.0"

    assert runtime_pipeline.version == "0.9.0"

    scene = create_scene()

    classifier = TrafficLightStateClassifier(
        minimum_saturation=(settings.traffic_light_minimum_saturation),
        minimum_value=(settings.traffic_light_minimum_value),
        minimum_active_pixel_ratio=(settings.traffic_light_minimum_active_pixel_ratio),
        dominance_ratio=(settings.traffic_light_dominance_ratio),
    )

    stabilizer = TrafficLightTemporalStabilizer(
        confirmation_frames=(settings.traffic_light_confirmation_frames),
        maximum_unknown_frames=(settings.traffic_light_maximum_unknown_frames),
        confidence_alpha=(settings.traffic_light_confidence_alpha),
    )

    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    job_id = uuid4()

    job_directory = OUTPUT_ROOT / str(job_id)

    source_path = OUTPUT_ROOT / (f"synthetic-input-{job_id}.mp4")

    source_writer = create_video_writer(source_path)

    artifact_writer = TrafficVideoArtifactWriter(
        root=OUTPUT_ROOT,
        job_id=job_id,
        preview_fps=(FRAMES_PER_SECOND),
        evidence_min_confidence=0.65,
        evidence_cooldown_frames=30,
        max_evidence_frames=0,
        preview_enabled=True,
    )

    raw_state_counts: Counter[str] = Counter()
    stable_state_counts: Counter[str] = Counter()
    transition_counts: Counter[str] = Counter()

    transition_records: list[dict[str, object]] = []

    frame_number = 0

    for phase_state, phase_frames in PHASES:
        for _ in range(phase_frames):
            frame_number += 1

            timestamp_seconds = (frame_number - 1) / FRAMES_PER_SECOND

            frame = create_synthetic_frame(
                state=phase_state,
                frame_number=frame_number,
            )

            source_writer.write(frame)

            raw_result = classifier.classify(
                frame=frame,
                scene=scene,
            )

            stable_result = stabilizer.update(
                frame_number=frame_number,
                timestamp_seconds=(timestamp_seconds),
                observations=raw_result,
            )

            annotated_frame = annotate_traffic_light_states(
                frame,
                scene=scene,
                states=stable_result.states,
            )

            for observation in raw_result.observations:
                raw_state_counts[observation.state.value] += 1

            for state in stable_result.states:
                stable_state_counts[state.stable_state.value] += 1

            for transition in stable_result.transitions:
                transition_key = (
                    f"{transition.previous_state.value}"
                    "_to_"
                    f"{transition.current_state.value}"
                )

                transition_counts[transition_key] += 1

                transition_records.append(
                    {
                        "frame_number": (transition.frame_number),
                        "timestamp_seconds": (transition.timestamp_seconds),
                        "previous_state": (transition.previous_state.value),
                        "current_state": (transition.current_state.value),
                        "confidence": (transition.confidence),
                    }
                )

            packet = FramePacket(
                frame_number=frame_number,
                timestamp_seconds=(timestamp_seconds),
                image=frame,
            )

            analysis = FrameAnalysis(
                traffic_light_observations=(raw_result.observations),
                traffic_light_states=(stable_result.states),
                traffic_light_transitions=(stable_result.transitions),
                annotated_frame=(annotated_frame),
            )

            artifact_writer.write(
                packet=packet,
                analysis=analysis,
            )

    source_writer.release()

    expected_frame_count = sum(phase_frames for _, phase_frames in PHASES)

    pipeline_summary = {
        "pipeline_name": ("yolo-traffic-pipeline"),
        "pipeline_version": (runtime_pipeline.version),
        "artifact_schema_version": "1.7",
        "validation_type": ("synthetic-traffic-light-state"),
        "processed_frames": frame_number,
        "raw_state_counts": dict(raw_state_counts),
        "stable_state_counts": dict(stable_state_counts),
        "transition_count": len(transition_records),
        "transition_counts": dict(transition_counts),
        "final_state": (stable_result.states[0].stable_state.value),
    }

    artifact_writer.finish(pipeline_summary=pipeline_summary)

    detections_path = job_directory / "detections.jsonl"

    assert detections_path.exists(), "Detection JSONL was not generated."

    records = read_jsonl(detections_path)

    assert len(records) == expected_frame_count

    assert all(record["schema_version"] == "1.7" for record in records)

    artifact_raw_states = {
        observation["state"]
        for record in records
        for observation in (record["traffic_lights"]["observations"])
    }

    artifact_stable_states = {
        state["stable_state"]
        for record in records
        for state in (record["traffic_lights"]["states"])
    }

    artifact_transition_count = sum(
        len(record["traffic_lights"]["transitions"]) for record in records
    )

    assert {
        "red",
        "yellow",
        "green",
        "unknown",
    }.issubset(artifact_raw_states)

    assert {
        "red",
        "yellow",
        "green",
        "unknown",
    }.issubset(artifact_stable_states)

    expected_transitions = {
        "unknown_to_red",
        "red_to_yellow",
        "yellow_to_green",
        "green_to_unknown",
    }

    assert expected_transitions.issubset(transition_counts.keys())

    assert artifact_transition_count == len(transition_records)

    assert pipeline_summary["final_state"] == "red"

    preview_path = find_preview(job_directory)

    decoded_preview_frames = verify_preview(preview_path)

    validation_summary = {
        **pipeline_summary,
        "job_id": str(job_id),
        "source_video": str(source_path),
        "preview_video": str(preview_path),
        "detections_jsonl": str(detections_path),
        "decoded_preview_frames": (decoded_preview_frames),
        "transitions": transition_records,
    }

    summary_path = job_directory / "validation_summary.json"

    summary_path.write_text(
        json.dumps(
            validation_summary,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    latest_link = replace_latest_link(
        output_root=OUTPUT_ROOT,
        job_id=job_id,
    )

    print()
    print("Traffic-light synthetic validation passed.")

    print(
        "Runtime pipeline version:",
        runtime_pipeline.version,
    )

    print(
        "Artifact schema version:",
        "1.7",
    )

    print(
        "Processed frames:",
        frame_number,
    )

    print(
        "Raw state counts:",
        dict(raw_state_counts),
    )

    print(
        "Stable state counts:",
        dict(stable_state_counts),
    )

    print(
        "Transitions:",
        transition_records,
    )

    print(
        "Decoded preview frames:",
        decoded_preview_frames,
    )

    print(
        "Source video:",
        source_path,
    )

    print(
        "Preview:",
        preview_path,
    )

    print(
        "JSONL:",
        detections_path,
    )

    print(
        "Summary:",
        summary_path,
    )

    print(
        "Latest validation:",
        latest_link,
    )


if __name__ == "__main__":
    main()
