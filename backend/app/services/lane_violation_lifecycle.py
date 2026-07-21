from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from app.models.enums import (
    ReviewStatus,
    ViolationType,
)
from app.models.violation_event import ViolationEvent
from app.reasoning.lane_violation import (
    LaneViolationSnapshot,
    LaneViolationTransition,
    LaneViolationTransitionType,
)
from app.tracking.types import TrackedObject


class LaneViolationEventStore(Protocol):
    """Repository operations used by lane persistence."""

    async def get_by_event_key(
        self,
        event_key: str,
        *,
        for_update: bool = False,
    ) -> ViolationEvent | None: ...

    async def create(
        self,
        event: ViolationEvent,
    ) -> ViolationEvent: ...

    async def commit(self) -> None: ...


class LaneViolationLifecycleMixin:
    """Persist lane-violation lifecycle transitions."""

    repository: LaneViolationEventStore

    async def persist_lane_violation_transitions(
        self,
        *,
        processing_job_id: UUID,
        video_id: UUID,
        camera_id: UUID | None,
        video_created_at: datetime,
        transitions: tuple[
            LaneViolationTransition,
            ...,
        ],
        states: tuple[
            LaneViolationSnapshot,
            ...,
        ],
        tracks: tuple[
            TrackedObject,
            ...,
        ],
    ) -> tuple[ViolationEvent, ...]:
        """Create or update durable lane-violation events."""

        if not transitions:
            return ()

        states_by_track = {state.track_id: state for state in states}

        tracks_by_id = {track.track_id: track for track in tracks}

        persisted_events: list[ViolationEvent] = []

        for transition in transitions:
            event_key = self.build_lane_violation_event_key(
                processing_job_id=(processing_job_id),
                transition=transition,
            )

            event = await self.repository.get_by_event_key(
                event_key,
                for_update=True,
            )

            state = states_by_track.get(transition.track_id)

            track = tracks_by_id.get(transition.track_id)

            detection_confidence = track.confidence if track is not None else None

            rule_confidence = self._lane_rule_confidence(
                state=state,
                transition=transition,
            )

            geometry = self._build_lane_geometry(
                transition=transition,
                track=track,
            )

            existing_metadata = event.event_metadata if event is not None else {}

            event_metadata = self._merge_lane_metadata(
                existing_metadata=(existing_metadata),
                transition=transition,
            )

            if event is None:
                occurred_at = self._calculate_lane_occurred_at(
                    video_created_at=(video_created_at),
                    transition=transition,
                )

                event = ViolationEvent(
                    video_id=video_id,
                    camera_id=camera_id,
                    processing_job_id=(processing_job_id),
                    event_key=event_key,
                    violation_type=(ViolationType.LANE_VIOLATION),
                    review_status=(ReviewStatus.PENDING),
                    occurred_at=occurred_at,
                    frame_number=(
                        transition.confirmed_frame or transition.frame_number
                    ),
                    track_id=str(transition.track_id),
                    license_plate=None,
                    detection_confidence=(detection_confidence),
                    rule_confidence=(rule_confidence),
                    ocr_confidence=None,
                    evidence_image_key=None,
                    evidence_clip_key=None,
                    geometry=geometry,
                    event_metadata=(event_metadata),
                )

                await self.repository.create(event)

            else:
                event.camera_id = event.camera_id or camera_id

                event.event_metadata = event_metadata

                if geometry:
                    event.geometry = geometry

                if detection_confidence is not None:
                    event.detection_confidence = max(
                        event.detection_confidence or 0.0,
                        detection_confidence,
                    )

                event.rule_confidence = max(
                    event.rule_confidence or 0.0,
                    rule_confidence,
                )

            persisted_events.append(event)

        await self.repository.commit()

        return tuple(persisted_events)

    @staticmethod
    def build_lane_violation_event_key(
        *,
        processing_job_id: UUID,
        transition: LaneViolationTransition,
    ) -> str:
        """Build an idempotent lane event key."""

        anchor_frame = transition.confirmed_frame or transition.first_candidate_frame

        return (
            f"lane_violation:{processing_job_id}:{transition.track_id}:{anchor_frame}"
        )

    @classmethod
    def _merge_lane_metadata(
        cls,
        *,
        existing_metadata: dict[
            str,
            Any,
        ],
        transition: LaneViolationTransition,
    ) -> dict[str, Any]:
        """Merge STARTED or ENDED metadata."""

        metadata = dict(existing_metadata or {})

        history = [
            dict(entry)
            for entry in metadata.get(
                "transition_history",
                [],
            )
            if isinstance(
                entry,
                dict,
            )
        ]

        transition_entry = {
            "type": (transition.transition_type.value),
            "frame_number": (transition.frame_number),
            "timestamp_seconds": (transition.timestamp_seconds),
            "nearest_lane_id": (transition.nearest_lane_id),
            "distance_to_nearest_lane_pixels": (
                transition.distance_to_nearest_lane_pixels
            ),
            "speed_pixels_per_second": (transition.speed_pixels_per_second),
        }

        identity = (
            transition_entry["type"],
            transition_entry["frame_number"],
        )

        already_recorded = any(
            (
                entry.get("type"),
                entry.get("frame_number"),
            )
            == identity
            for entry in history
        )

        if not already_recorded:
            history.append(transition_entry)

        start_timestamp_seconds = max(
            transition.timestamp_seconds - transition.duration_seconds,
            0.0,
        )

        metadata.update(
            {
                "lifecycle_status": (
                    "ended"
                    if (transition.transition_type == LaneViolationTransitionType.ENDED)
                    else "active"
                ),
                "class_name": (transition.class_name),
                "nearest_lane_id": (transition.nearest_lane_id),
                "distance_to_nearest_lane_pixels": (
                    transition.distance_to_nearest_lane_pixels
                ),
                "speed_pixels_per_second": (transition.speed_pixels_per_second),
                "first_candidate_frame": (transition.first_candidate_frame),
                "confirmed_frame": (transition.confirmed_frame),
                "start_frame": (
                    transition.confirmed_frame or transition.first_candidate_frame
                ),
                "start_timestamp_seconds": (start_timestamp_seconds),
                "last_transition_frame": (transition.frame_number),
                "last_transition_timestamp_seconds": (transition.timestamp_seconds),
                "transition_history": (history),
            }
        )

        if transition.transition_type == LaneViolationTransitionType.ENDED:
            metadata.update(
                {
                    "end_frame": (transition.frame_number),
                    "end_timestamp_seconds": (transition.timestamp_seconds),
                    "duration_seconds": (transition.duration_seconds),
                }
            )

        return metadata

    @staticmethod
    def _build_lane_geometry(
        *,
        transition: LaneViolationTransition,
        track: TrackedObject | None,
    ) -> dict[str, Any]:
        """Build reviewable event geometry."""

        geometry: dict[str, Any] = {
            "road_anchor": {
                "x_normalized": (transition.anchor_x_normalized),
                "y_normalized": (transition.anchor_y_normalized),
            },
            "nearest_lane_id": (transition.nearest_lane_id),
            "distance_to_nearest_lane_pixels": (
                transition.distance_to_nearest_lane_pixels
            ),
            "velocity": {
                "x_pixels_per_second": (transition.velocity_x),
                "y_pixels_per_second": (transition.velocity_y),
                "speed_pixels_per_second": (transition.speed_pixels_per_second),
            },
        }

        if track is not None:
            box = track.bounding_box

            geometry["bounding_box"] = {
                "x1": box.x1,
                "y1": box.y1,
                "x2": box.x2,
                "y2": box.y2,
                "width": box.width,
                "height": box.height,
            }

        return geometry

    @staticmethod
    def _lane_rule_confidence(
        *,
        state: LaneViolationSnapshot | None,
        transition: LaneViolationTransition,
    ) -> float:
        """
        Return a bounded severity score.

        This is a rule-strength score, not a calibrated
        probability.
        """

        distance = (
            state.distance_to_nearest_lane_pixels
            if state is not None
            else transition.distance_to_nearest_lane_pixels
        )

        speed = (
            state.speed_pixels_per_second
            if state is not None
            else transition.speed_pixels_per_second
        )

        distance_value = max(
            distance or 0.0,
            0.0,
        )

        speed_value = max(
            speed,
            0.0,
        )

        distance_score = distance_value / (distance_value + 25.0)

        speed_score = speed_value / (speed_value + 25.0)

        return min(
            max(
                (distance_score + speed_score) / 2.0,
                0.0,
            ),
            1.0,
        )

    @staticmethod
    def _calculate_lane_occurred_at(
        *,
        video_created_at: datetime,
        transition: LaneViolationTransition,
    ) -> datetime:
        """Calculate the violation start time."""

        start_seconds = max(
            transition.timestamp_seconds - transition.duration_seconds,
            0.0,
        )

        return video_created_at + timedelta(seconds=start_seconds)
