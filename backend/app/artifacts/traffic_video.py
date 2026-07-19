import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TextIO
from uuid import UUID

import cv2

from app.detection.types import Detection
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
)


@dataclass(frozen=True)
class ArtifactSummary:
    """Storage keys produced by one processing job."""

    root_key: str
    detections_key: str
    summary_key: str
    preview_key: str | None
    evidence_keys: tuple[str, ...]
    analyzed_frames: int

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)


class TrafficVideoArtifactWriter:
    """Write YOLO detections and visual evidence."""

    def __init__(
        self,
        *,
        root: Path,
        job_id: UUID,
        preview_fps: float,
        evidence_min_confidence: float,
        evidence_cooldown_frames: int,
        max_evidence_frames: int,
        preview_enabled: bool,
    ) -> None:
        self.root = root.resolve()
        self.job_id = job_id

        self.preview_fps = max(
            preview_fps,
            1.0,
        )

        self.evidence_min_confidence = evidence_min_confidence

        self.evidence_cooldown_frames = max(
            evidence_cooldown_frames,
            0,
        )

        self.max_evidence_frames = max(
            max_evidence_frames,
            0,
        )

        self.preview_enabled = preview_enabled

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.root_key = str(job_id)

        self.temporary_directory = self.root / f".{job_id}.part"

        self.final_directory = self.root / str(job_id)

        if self.temporary_directory.exists():
            shutil.rmtree(self.temporary_directory)

        self.temporary_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.evidence_directory = self.temporary_directory / "evidence"

        self.evidence_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.detections_path = self.temporary_directory / "detections.jsonl"

        self.summary_path = self.temporary_directory / "summary.json"

        self.preview_filename = "annotated-preview.mp4"

        self.preview_path = self.temporary_directory / self.preview_filename

        self.detections_file: TextIO = open(
            self.detections_path,
            mode="w",
            encoding="utf-8",
        )

        self.preview_writer: cv2.VideoWriter | None = None

        self.evidence_keys: list[str] = []

        self.analyzed_frames = 0
        self.last_evidence_frame: int | None = None

        self.finished = False

    def write(
        self,
        *,
        packet: FramePacket,
        analysis: FrameAnalysis,
    ) -> None:
        """Write outputs for one analyzed frame."""

        if not analysis.analyzed:
            return

        self.analyzed_frames += 1

        record = {
            "schema_version": "1.0",
            "frame_number": packet.frame_number,
            "timestamp_seconds": (packet.timestamp_seconds),
            "image_width": int(packet.image.shape[1]),
            "image_height": int(packet.image.shape[0]),
            "metrics": analysis.metrics,
            "detections": [
                self._serialize_detection(detection)
                for detection in analysis.detections
            ],
        }

        self.detections_file.write(
            json.dumps(
                record,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        )

        if analysis.annotated_frame is not None:
            self._write_preview_frame(analysis.annotated_frame)

            self._maybe_write_evidence(
                packet=packet,
                analysis=analysis,
            )

    def finish(
        self,
        *,
        pipeline_summary: dict[str, Any],
    ) -> ArtifactSummary:
        """Finalize outputs and atomically publish them."""

        self._close_resources()

        preview_key: str | None = None

        if self.preview_enabled and self.preview_path.exists():
            preview_key = f"{self.root_key}/{self.preview_filename}"

        artifact_summary = ArtifactSummary(
            root_key=self.root_key,
            detections_key=(f"{self.root_key}/detections.jsonl"),
            summary_key=(f"{self.root_key}/summary.json"),
            preview_key=preview_key,
            evidence_keys=tuple(self.evidence_keys),
            analyzed_frames=(self.analyzed_frames),
        )

        summary_payload = {
            "job_id": str(self.job_id),
            "pipeline": pipeline_summary,
            "artifacts": (artifact_summary.as_dict()),
        }

        with open(
            self.summary_path,
            mode="w",
            encoding="utf-8",
        ) as summary_file:
            json.dump(
                summary_payload,
                summary_file,
                ensure_ascii=False,
                indent=2,
            )

        if self.final_directory.exists():
            shutil.rmtree(self.final_directory)

        os.replace(
            self.temporary_directory,
            self.final_directory,
        )

        self.finished = True

        return artifact_summary

    def abort(self) -> None:
        """Remove incomplete artifacts after a failure."""

        if self.finished:
            return

        self._close_resources()

        if self.temporary_directory.exists():
            shutil.rmtree(self.temporary_directory)

    def _write_preview_frame(
        self,
        frame,
    ) -> None:
        if not self.preview_enabled:
            return

        if self.preview_writer is None:
            height, width = frame.shape[:2]

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")

            self.preview_writer = cv2.VideoWriter(
                str(self.preview_path),
                fourcc,
                self.preview_fps,
                (width, height),
            )

            if not self.preview_writer.isOpened():
                self.preview_writer.release()
                self.preview_writer = None

                raise RuntimeError(
                    "Could not initialize annotated preview video writer."
                )

        self.preview_writer.write(frame)

    def _maybe_write_evidence(
        self,
        *,
        packet: FramePacket,
        analysis: FrameAnalysis,
    ) -> None:
        if not analysis.detections:
            return

        if len(self.evidence_keys) >= self.max_evidence_frames:
            return

        maximum_confidence = max(
            detection.confidence for detection in analysis.detections
        )

        if maximum_confidence < self.evidence_min_confidence:
            return

        if self.last_evidence_frame is not None:
            frames_since_previous = packet.frame_number - self.last_evidence_frame

            if frames_since_previous < self.evidence_cooldown_frames:
                return

        filename = f"frame-{packet.frame_number:06d}.jpg"

        path = self.evidence_directory / filename

        successful_write = cv2.imwrite(
            str(path),
            analysis.annotated_frame,
        )

        if not successful_write:
            raise RuntimeError(f"Could not write evidence image: {path}")

        key = f"{self.root_key}/evidence/{filename}"

        self.evidence_keys.append(key)
        self.last_evidence_frame = packet.frame_number

    def _close_resources(self) -> None:
        if not self.detections_file.closed:
            self.detections_file.flush()
            self.detections_file.close()

        if self.preview_writer is not None:
            self.preview_writer.release()
            self.preview_writer = None

    @staticmethod
    def _serialize_detection(
        detection: Detection,
    ) -> dict[str, Any]:
        box = detection.bounding_box

        return {
            "class_id": detection.class_id,
            "class_name": detection.class_name,
            "confidence": detection.confidence,
            "model_name": detection.model_name,
            "bounding_box": {
                "x1": box.x1,
                "y1": box.y1,
                "x2": box.x2,
                "y2": box.y2,
                "width": box.width,
                "height": box.height,
                "area": box.area,
                "center": list(box.center),
            },
        }
