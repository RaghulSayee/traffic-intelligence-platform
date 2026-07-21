from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import UUID

from app.models.enums import (
    ReviewStatus,
    ViolationType,
)
from app.models.violation_event import ViolationEvent
from app.reasoning.red_light import (
    RedLightViolationTransition,
)


class RedLightEventStore(Protocol):
    """Repository operations required for red-light persistence."""

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


class RedLightLifecycleMixin:
    """Persist red-light stop-line crossings as violation events."""

    repository: RedLightEventStore

    async def persist_red_light_transitions(
        self,
        *,
        processing_job_id: UUID,
        video_id: UUID,
        camera_id: UUID | None,
        video_created_at: datetime,
        transitions: tuple[
            RedLightViolationTransition,
            ...,
        ],
    ) -> tuple[
        ViolationEvent,
        ...,
    ]:
        """
        Create or update durable red-light violations.

        The event key makes replaying the same processing transition
        idempotent.
        """

        if not transitions:
            return ()

        persisted_events: list[ViolationEvent] = []

        for transition in transitions:
            event_key = self.build_red_light_event_key(
                processing_job_id=(processing_job_id),
                transition=transition,
            )

            event = await self.repository.get_by_event_key(
                event_key,
                for_update=True,
            )

            geometry = self._build_red_light_geometry(transition)

            existing_metadata = event.event_metadata if event is not None else {}

            event_metadata = self._merge_red_light_metadata(
                existing_metadata=(existing_metadata),
                transition=transition,
            )

            if event is None:
                event = ViolationEvent(
                    video_id=video_id,
                    camera_id=camera_id,
                    processing_job_id=(processing_job_id),
                    event_key=event_key,
                    violation_type=(ViolationType.RED_LIGHT),
                    review_status=(ReviewStatus.PENDING),
                    occurred_at=(
                        self._red_light_occurred_at(
                            video_created_at=(video_created_at),
                            transition=transition,
                        )
                    ),
                    frame_number=(transition.frame_number),
                    track_id=str(transition.track_id),
                    license_plate=None,
                    detection_confidence=(transition.detection_confidence),
                    rule_confidence=(transition.rule_confidence),
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

                event.geometry = geometry

                event.detection_confidence = max(
                    event.detection_confidence or 0.0,
                    transition.detection_confidence,
                )

                event.rule_confidence = max(
                    event.rule_confidence or 0.0,
                    transition.rule_confidence,
                )

            persisted_events.append(event)

        await self.repository.commit()

        return tuple(persisted_events)

    @staticmethod
    def build_red_light_event_key(
        *,
        processing_job_id: UUID,
        transition: RedLightViolationTransition,
    ) -> str:
        """Build the deterministic red-light event key."""

        return (
            "red_light:"
            f"{processing_job_id}:"
            f"{transition.track_id}:"
            f"{transition.stop_line_id}:"
            f"{transition.frame_number}"
        )

    @staticmethod
    def _red_light_occurred_at(
        *,
        video_created_at: datetime,
        transition: RedLightViolationTransition,
    ) -> datetime:
        """Convert the video timestamp into an event datetime."""

        base_datetime = video_created_at

        if base_datetime.tzinfo is None:
            base_datetime = base_datetime.replace(tzinfo=timezone.utc)

        return base_datetime + timedelta(
            seconds=max(
                transition.timestamp_seconds,
                0.0,
            )
        )

    @staticmethod
    def _build_red_light_geometry(
        transition: RedLightViolationTransition,
    ) -> dict[str, Any]:
        """Build reviewable stop-line crossing geometry."""

        return {
            "stop_line_id": (transition.stop_line_id),
            "lane_id": (transition.lane_id),
            "traffic_light_region_id": (transition.traffic_light_region_id),
            "previous_anchor_normalized": {
                "x": (transition.previous_anchor_x_normalized),
                "y": (transition.previous_anchor_y_normalized),
            },
            "anchor_normalized": {
                "x": (transition.anchor_x_normalized),
                "y": (transition.anchor_y_normalized),
            },
            "previous_signed_distance_pixels": (
                transition.previous_signed_distance_pixels
            ),
            "signed_distance_pixels": (transition.signed_distance_pixels),
            "crossing_depth_pixels": (transition.crossing_depth_pixels),
            "velocity_pixels_per_second": {
                "x": transition.velocity_x,
                "y": transition.velocity_y,
                "speed": (transition.speed_pixels_per_second),
            },
            "direction_cosine": (transition.direction_cosine),
        }

    @classmethod
    def _merge_red_light_metadata(
        cls,
        *,
        existing_metadata: dict[
            str,
            Any,
        ],
        transition: RedLightViolationTransition,
    ) -> dict[str, Any]:
        """Merge transition metadata without duplicating replay history."""

        metadata = dict(existing_metadata or {})

        transition_entry = cls._red_light_transition_metadata(transition)

        history = list(
            metadata.get(
                "transition_history",
                [],
            )
        )

        transition_signature = transition_entry["transition_signature"]

        existing_signatures = {
            entry.get("transition_signature")
            for entry in history
            if isinstance(
                entry,
                dict,
            )
        }

        if transition_signature not in existing_signatures:
            history.append(transition_entry)

        metadata.update(
            {
                "status": "started",
                "class_name": (transition.class_name),
                "stop_line_id": (transition.stop_line_id),
                "lane_id": (transition.lane_id),
                "traffic_light_region_id": (transition.traffic_light_region_id),
                "signal_state": (transition.signal_state.value),
                "signal_confidence": (transition.signal_confidence),
                "direction_cosine": (transition.direction_cosine),
                "speed_pixels_per_second": (transition.speed_pixels_per_second),
                "transition_history": history,
            }
        )

        return metadata

    @staticmethod
    def _red_light_transition_metadata(
        transition: RedLightViolationTransition,
    ) -> dict[str, Any]:
        """Serialize one lifecycle transition into event metadata."""

        transition_signature = (
            f"{transition.transition_type.value}:"
            f"{transition.track_id}:"
            f"{transition.stop_line_id}:"
            f"{transition.frame_number}"
        )

        return {
            "transition_signature": (transition_signature),
            "transition_type": (transition.transition_type.value),
            "frame_number": (transition.frame_number),
            "previous_frame_number": (transition.previous_frame_number),
            "timestamp_seconds": (transition.timestamp_seconds),
            "signal_state": (transition.signal_state.value),
            "signal_confidence": (transition.signal_confidence),
            "detection_confidence": (transition.detection_confidence),
            "rule_confidence": (transition.rule_confidence),
            "crossing_depth_pixels": (transition.crossing_depth_pixels),
        }
