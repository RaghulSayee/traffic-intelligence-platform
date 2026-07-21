import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TextIO
from uuid import UUID
from app.tracking.types import TrackedObject

import cv2

from app.detection.types import Detection
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
)
from app.reasoning.helmet_rider import (
    HelmetRiderAssociation,
)
from app.reasoning.lane_occupancy import (
    LaneOccupancyObservation,
)
from app.reasoning.lane_violation import (
    LaneViolationSnapshot,
    LaneViolationTransition,
)
from app.reasoning.no_helmet import (
    NoHelmetTransition,
    NoHelmetViolationSnapshot,
)
from app.reasoning.temporal_rider import (
    TemporalRiderAssociation,
)
from app.reasoning.triple_riding import (
    TripleRidingTransition,
    TripleRidingViolationSnapshot,
)
from app.reasoning.wrong_way import (
    WrongWayTransition,
    WrongWayViolationSnapshot,
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
            "schema_version": "1.5",
            "frame_number": packet.frame_number,
            "timestamp_seconds": (packet.timestamp_seconds),
            "image_width": int(packet.image.shape[1]),
            "image_height": int(packet.image.shape[0]),
            "metrics": analysis.metrics,
            "detections": [
                self._serialize_detection(detection)
                for detection in analysis.detections
            ],
            "helmet_analysis": {
                "detections": [
                    self._serialize_detection(detection)
                    for detection in analysis.helmet_detections
                ],
                "rider_associations": [
                    self._serialize_helmet_rider_association(association)
                    for association in analysis.helmet_rider_associations
                ],
                "no_helmet": {
                    "states": [
                        self._serialize_no_helmet_state(state)
                        for state in analysis.no_helmet_states
                    ],
                    "transitions": [
                        self._serialize_no_helmet_transition(transition)
                        for transition in analysis.no_helmet_transitions
                    ],
                },
            },
            "lane_analysis": {
                "occupancy": [
                    self._serialize_lane_occupancy(observation)
                    for observation in analysis.lane_occupancy_observations
                ],
                "violations": {
                    "states": [
                        self._serialize_lane_violation_state(state)
                        for state in analysis.lane_violation_states
                    ],
                    "transitions": [
                        self._serialize_lane_violation_transition(transition)
                        for transition in analysis.lane_violation_transitions
                    ],
                },
            },
            "road_rules": {
                "wrong_way": {
                    "states": [
                        self._serialize_wrong_way_state(state)
                        for state in analysis.wrong_way_states
                    ],
                    "transitions": [
                        self._serialize_wrong_way_transition(transition)
                        for transition in analysis.wrong_way_transitions
                    ],
                },
            },
            "tracks": [self._serialize_track(track) for track in analysis.tracks],
            "rider_associations": [
                self._serialize_rider_association(association)
                for association in analysis.rider_associations
            ],
            "triple_riding": {
                "states": [
                    self._serialize_triple_riding_state(state)
                    for state in analysis.triple_riding_states
                ],
                "transitions": [
                    self._serialize_triple_riding_transition(transition)
                    for transition in analysis.triple_riding_transitions
                ],
            },
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
        """Write detection or violation evidence."""

        if (
            self.max_evidence_frames <= 0
            or len(self.evidence_keys) >= self.max_evidence_frames
        ):
            return

        transition_groups = (
            analysis.triple_riding_transitions,
            analysis.no_helmet_transitions,
            analysis.wrong_way_transitions,
            analysis.lane_violation_transitions,
        )

        has_started_violation = any(
            getattr(
                transition.transition_type,
                "value",
                str(transition.transition_type),
            )
            == "started"
            for transitions in transition_groups
            for transition in transitions
        )

        if not has_started_violation:
            if not analysis.detections:
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

    @staticmethod
    def _serialize_track(
        track: TrackedObject,
    ) -> dict[str, Any]:
        """Convert one track into JSON-compatible values."""

        box = track.bounding_box

        return {
            "track_id": track.track_id,
            "class_id": track.class_id,
            "class_name": track.class_name,
            "confidence": track.confidence,
            "confirmed": track.confirmed,
            "age": track.age,
            "hits": track.hits,
            "missed_frames": track.missed_frames,
            "velocity": {
                "x_pixels_per_second": (track.velocity_x),
                "y_pixels_per_second": (track.velocity_y),
            },
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

    @staticmethod
    def _serialize_rider_association(
        association: TemporalRiderAssociation,
    ) -> dict[str, Any]:
        """Serialize a temporal rider relationship."""

        features = association.features

        return {
            "person_track_id": (association.person_track_id),
            "motorcycle_track_id": (association.motorcycle_track_id),
            "latest_score": association.latest_score,
            "smoothed_score": (association.smoothed_score),
            "consecutive_matches": (association.consecutive_matches),
            "total_matches": (association.total_matches),
            "missed_frames": (association.missed_frames),
            "confirmed": association.confirmed,
            "observed_this_frame": (association.observed_this_frame),
            "features": {
                "horizontal_overlap_score": (features.horizontal_overlap_score),
                "anchor_distance_score": (features.anchor_distance_score),
                "vertical_position_score": (features.vertical_position_score),
                "motion_similarity_score": (features.motion_similarity_score),
                "containment_score": (features.containment_score),
            },
        }

    @staticmethod
    def _serialize_helmet_rider_association(
        association: HelmetRiderAssociation,
    ) -> dict[str, Any]:
        """Serialize a helmet-to-rider relationship."""

        return {
            "person_track_id": (association.person_track_id),
            "motorcycle_track_id": (association.motorcycle_track_id),
            "class_name": association.class_name,
            "detection_confidence": (association.detection_confidence),
            "association_score": (association.association_score),
            "head_region": {
                "x1": association.head_region.x1,
                "y1": association.head_region.y1,
                "x2": association.head_region.x2,
                "y2": association.head_region.y2,
            },
            "detection_box": {
                "x1": association.detection_box.x1,
                "y1": association.detection_box.y1,
                "x2": association.detection_box.x2,
                "y2": association.detection_box.y2,
            },
        }

    @staticmethod
    def _serialize_no_helmet_state(
        state: NoHelmetViolationSnapshot,
    ) -> dict[str, Any]:
        """Serialize a no-helmet state."""

        return {
            "person_track_id": state.person_track_id,
            "motorcycle_track_id": (state.motorcycle_track_id),
            "detection_confidence": (state.detection_confidence),
            "association_score": (state.association_score),
            "first_candidate_frame": (state.first_candidate_frame),
            "confirmed_frame": state.confirmed_frame,
            "last_violation_frame": (state.last_violation_frame),
            "consecutive_violation_frames": (state.consecutive_violation_frames),
            "missed_frames": state.missed_frames,
            "confirmed": state.confirmed,
            "observed_this_frame": (state.observed_this_frame),
        }

    @staticmethod
    def _serialize_no_helmet_transition(
        transition: NoHelmetTransition,
    ) -> dict[str, Any]:
        """Serialize a no-helmet lifecycle transition."""

        return {
            "transition_type": (transition.transition_type.value),
            "person_track_id": (transition.person_track_id),
            "motorcycle_track_id": (transition.motorcycle_track_id),
            "detection_confidence": (transition.detection_confidence),
            "association_score": (transition.association_score),
            "frame_number": transition.frame_number,
            "timestamp_seconds": (transition.timestamp_seconds),
            "first_candidate_frame": (transition.first_candidate_frame),
            "confirmed_frame": (transition.confirmed_frame),
            "duration_seconds": (transition.duration_seconds),
        }

    @staticmethod
    def _serialize_triple_riding_state(
        state: TripleRidingViolationSnapshot,
    ) -> dict[str, Any]:
        """Serialize a triple-riding state."""

        return {
            "motorcycle_track_id": (state.motorcycle_track_id),
            "rider_track_ids": list(state.rider_track_ids),
            "rider_count": state.rider_count,
            "peak_rider_count": (state.peak_rider_count),
            "average_association_score": (state.average_association_score),
            "first_candidate_frame": (state.first_candidate_frame),
            "confirmed_frame": (state.confirmed_frame),
            "last_violation_frame": (state.last_violation_frame),
            "consecutive_violation_frames": (state.consecutive_violation_frames),
            "missed_frames": state.missed_frames,
            "confirmed": state.confirmed,
            "observed_this_frame": (state.observed_this_frame),
        }

    @staticmethod
    def _serialize_triple_riding_transition(
        transition: TripleRidingTransition,
    ) -> dict[str, Any]:
        """Serialize a violation lifecycle transition."""

        return {
            "transition_type": (transition.transition_type.value),
            "motorcycle_track_id": (transition.motorcycle_track_id),
            "rider_track_ids": list(transition.rider_track_ids),
            "rider_count": (transition.rider_count),
            "peak_rider_count": (transition.peak_rider_count),
            "frame_number": (transition.frame_number),
            "timestamp_seconds": (transition.timestamp_seconds),
            "first_candidate_frame": (transition.first_candidate_frame),
            "confirmed_frame": (transition.confirmed_frame),
            "duration_seconds": (transition.duration_seconds),
        }

    @staticmethod
    def _serialize_lane_occupancy(
        observation: LaneOccupancyObservation,
    ) -> dict[str, Any]:
        """Serialize one lane occupancy observation."""

        return {
            "track_id": observation.track_id,
            "class_name": observation.class_name,
            "lane_id": observation.lane_id,
            "nearest_lane_id": (observation.nearest_lane_id),
            "anchor": {
                "x_normalized": (observation.anchor_x_normalized),
                "y_normalized": (observation.anchor_y_normalized),
            },
            "distance_to_nearest_lane_pixels": (
                observation.distance_to_nearest_lane_pixels
            ),
            "velocity": {
                "x_pixels_per_second": (observation.velocity_x),
                "y_pixels_per_second": (observation.velocity_y),
                "speed_pixels_per_second": (observation.speed_pixels_per_second),
            },
            "inside_monitoring_zone": (observation.inside_monitoring_zone),
            "outside_configured_lanes": (observation.outside_configured_lanes),
            "within_boundary_tolerance": (observation.within_boundary_tolerance),
            "violation_candidate": (observation.violation_candidate),
        }

    @staticmethod
    def _serialize_lane_violation_state(
        state: LaneViolationSnapshot,
    ) -> dict[str, Any]:
        """Serialize one temporal lane state."""

        return {
            "track_id": state.track_id,
            "class_name": state.class_name,
            "nearest_lane_id": (state.nearest_lane_id),
            "anchor": {
                "x_normalized": (state.anchor_x_normalized),
                "y_normalized": (state.anchor_y_normalized),
            },
            "distance_to_nearest_lane_pixels": (state.distance_to_nearest_lane_pixels),
            "speed_pixels_per_second": (state.speed_pixels_per_second),
            "first_candidate_frame": (state.first_candidate_frame),
            "confirmed_frame": (state.confirmed_frame),
            "last_violation_frame": (state.last_violation_frame),
            "consecutive_violation_frames": (state.consecutive_violation_frames),
            "missed_frames": state.missed_frames,
            "confirmed": state.confirmed,
            "observed_this_frame": (state.observed_this_frame),
        }

    @staticmethod
    def _serialize_lane_violation_transition(
        transition: LaneViolationTransition,
    ) -> dict[str, Any]:
        """Serialize one lane lifecycle transition."""

        return {
            "transition_type": (transition.transition_type.value),
            "track_id": transition.track_id,
            "class_name": transition.class_name,
            "nearest_lane_id": (transition.nearest_lane_id),
            "anchor": {
                "x_normalized": (transition.anchor_x_normalized),
                "y_normalized": (transition.anchor_y_normalized),
            },
            "distance_to_nearest_lane_pixels": (
                transition.distance_to_nearest_lane_pixels
            ),
            "velocity": {
                "x_pixels_per_second": (transition.velocity_x),
                "y_pixels_per_second": (transition.velocity_y),
                "speed_pixels_per_second": (transition.speed_pixels_per_second),
            },
            "frame_number": (transition.frame_number),
            "timestamp_seconds": (transition.timestamp_seconds),
            "first_candidate_frame": (transition.first_candidate_frame),
            "confirmed_frame": (transition.confirmed_frame),
            "duration_seconds": (transition.duration_seconds),
        }

    @staticmethod
    def _serialize_wrong_way_state(
        state: WrongWayViolationSnapshot,
    ) -> dict[str, Any]:
        """Serialize one wrong-way state."""

        return {
            "track_id": state.track_id,
            "class_name": state.class_name,
            "lane_id": state.lane_id,
            "velocity": {
                "x": state.velocity_x,
                "y": state.velocity_y,
            },
            "speed_pixels_per_second": (state.speed_pixels_per_second),
            "cosine_similarity": (state.cosine_similarity),
            "opposition_score": (state.opposition_score),
            "first_candidate_frame": (state.first_candidate_frame),
            "confirmed_frame": (state.confirmed_frame),
            "last_violation_frame": (state.last_violation_frame),
            "consecutive_violation_frames": (state.consecutive_violation_frames),
            "missed_frames": state.missed_frames,
            "confirmed": state.confirmed,
            "observed_this_frame": (state.observed_this_frame),
        }

    @staticmethod
    def _serialize_wrong_way_transition(
        transition: WrongWayTransition,
    ) -> dict[str, Any]:
        """Serialize one wrong-way lifecycle transition."""

        return {
            "type": transition.transition_type.value,
            "track_id": transition.track_id,
            "class_name": transition.class_name,
            "lane_id": transition.lane_id,
            "velocity": {
                "x": transition.velocity_x,
                "y": transition.velocity_y,
            },
            "speed_pixels_per_second": (transition.speed_pixels_per_second),
            "cosine_similarity": (transition.cosine_similarity),
            "opposition_score": (transition.opposition_score),
            "frame_number": (transition.frame_number),
            "timestamp_seconds": (transition.timestamp_seconds),
            "first_candidate_frame": (transition.first_candidate_frame),
            "confirmed_frame": (transition.confirmed_frame),
            "duration_seconds": (transition.duration_seconds),
        }
