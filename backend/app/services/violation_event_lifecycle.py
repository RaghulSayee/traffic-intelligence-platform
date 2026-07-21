from __future__ import annotations
import re

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    ReviewStatus,
    ViolationType,
)
from app.models.violation_event import ViolationEvent
from app.reasoning.no_helmet import (
    NoHelmetTransition,
    NoHelmetTransitionType,
    NoHelmetViolationSnapshot,
)
from app.reasoning.triple_riding import (
    TripleRidingTransition,
    TripleRidingTransitionType,
    TripleRidingViolationSnapshot,
)
from app.reasoning.wrong_way import (
    WrongWayTransition,
    WrongWayTransitionType,
    WrongWayViolationSnapshot,
)
from app.services.red_light_lifecycle import (
    RedLightLifecycleMixin,
)
from app.services.lane_violation_lifecycle import (
    LaneViolationLifecycleMixin,
)
from app.repositories.violation_event import (
    ViolationEventRepository,
)
from app.tracking.types import TrackedObject


class ViolationEventStore(Protocol):
    """Storage operations required by the lifecycle service."""

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

    async def list_by_processing_job(
        self,
        processing_job_id: UUID,
        *,
        for_update: bool = False,
    ) -> list[ViolationEvent]: ...

    async def commit(self) -> None: ...


class ViolationEventLifecycleService(
    RedLightLifecycleMixin,
    LaneViolationLifecycleMixin,
):
    """
    Convert reasoning transitions into durable violation events.

    Repeated processing of the same transition updates the existing
    event rather than creating a duplicate database row.
    """

    def __init__(
        self,
        session: AsyncSession | None = None,
        *,
        repository: ViolationEventStore | None = None,
    ) -> None:
        if repository is None:
            if session is None:
                raise ValueError("A database session or repository is required.")

            repository = ViolationEventRepository(session)

        self.repository = repository

    async def persist_triple_riding_transitions(
        self,
        *,
        processing_job_id: UUID,
        video_id: UUID,
        camera_id: UUID | None,
        video_created_at: datetime,
        transitions: tuple[
            TripleRidingTransition,
            ...,
        ],
        states: tuple[
            TripleRidingViolationSnapshot,
            ...,
        ],
        tracks: tuple[TrackedObject, ...],
    ) -> tuple[ViolationEvent, ...]:
        """Create or update triple-riding events."""

        if not transitions:
            return ()

        states_by_motorcycle = {state.motorcycle_track_id: state for state in states}

        tracks_by_id = {track.track_id: track for track in tracks}

        persisted_events: list[ViolationEvent] = []

        for transition in transitions:
            event_key = self.build_triple_riding_event_key(
                processing_job_id=(processing_job_id),
                transition=transition,
            )

            event = await self.repository.get_by_event_key(
                event_key,
                for_update=True,
            )

            state = states_by_motorcycle.get(transition.motorcycle_track_id)

            rule_confidence = self._rule_confidence(state)

            geometry = self._build_geometry(
                transition=transition,
                tracks_by_id=tracks_by_id,
            )

            existing_metadata = event.event_metadata if event is not None else {}

            event_metadata = self._merge_metadata(
                existing_metadata=existing_metadata,
                transition=transition,
            )

            if event is None:
                occurred_at = self._calculate_occurred_at(
                    video_created_at=(video_created_at),
                    transition=transition,
                )

                event = ViolationEvent(
                    video_id=video_id,
                    camera_id=camera_id,
                    processing_job_id=(processing_job_id),
                    event_key=event_key,
                    violation_type=(ViolationType.TRIPLE_RIDING),
                    review_status=(ReviewStatus.PENDING),
                    occurred_at=occurred_at,
                    frame_number=(
                        transition.confirmed_frame or transition.frame_number
                    ),
                    track_id=str(transition.motorcycle_track_id),
                    license_plate=None,
                    detection_confidence=None,
                    rule_confidence=(rule_confidence),
                    ocr_confidence=None,
                    evidence_image_key=None,
                    evidence_clip_key=None,
                    geometry=geometry,
                    event_metadata=event_metadata,
                )

                await self.repository.create(event)

            else:
                event.camera_id = event.camera_id or camera_id

                event.event_metadata = event_metadata

                if geometry:
                    event.geometry = geometry

                if rule_confidence is not None:
                    event.rule_confidence = max(
                        event.rule_confidence or 0.0,
                        rule_confidence,
                    )

            persisted_events.append(event)

        await self.repository.commit()

        return tuple(persisted_events)

    async def persist_no_helmet_transitions(
        self,
        *,
        processing_job_id: UUID,
        video_id: UUID,
        camera_id: UUID | None,
        video_created_at: datetime,
        transitions: tuple[
            NoHelmetTransition,
            ...,
        ],
        states: tuple[
            NoHelmetViolationSnapshot,
            ...,
        ],
        tracks: tuple[TrackedObject, ...],
    ) -> tuple[ViolationEvent, ...]:
        """Create or update durable no-helmet events."""

        if not transitions:
            return ()

        states_by_person = {state.person_track_id: state for state in states}

        tracks_by_id = {track.track_id: track for track in tracks}

        persisted_events: list[ViolationEvent] = []

        for transition in transitions:
            event_key = self.build_no_helmet_event_key(
                processing_job_id=(processing_job_id),
                transition=transition,
            )

            event = await self.repository.get_by_event_key(
                event_key,
                for_update=True,
            )

            state = states_by_person.get(transition.person_track_id)

            detection_confidence = (
                state.detection_confidence
                if state is not None
                else transition.detection_confidence
            )

            rule_confidence = (
                state.association_score
                if state is not None
                else transition.association_score
            )

            geometry = self._build_no_helmet_geometry(
                transition=transition,
                tracks_by_id=tracks_by_id,
            )

            existing_metadata = event.event_metadata if event is not None else {}

            event_metadata = self._merge_no_helmet_metadata(
                existing_metadata=(existing_metadata),
                transition=transition,
            )

            if event is None:
                occurred_at = self._calculate_occurred_at(
                    video_created_at=(video_created_at),
                    transition=transition,
                )

                event = ViolationEvent(
                    video_id=video_id,
                    camera_id=camera_id,
                    processing_job_id=(processing_job_id),
                    event_key=event_key,
                    violation_type=(ViolationType.NO_HELMET),
                    review_status=(ReviewStatus.PENDING),
                    occurred_at=occurred_at,
                    frame_number=(
                        transition.confirmed_frame or transition.frame_number
                    ),
                    track_id=str(transition.person_track_id),
                    license_plate=None,
                    detection_confidence=(detection_confidence),
                    rule_confidence=(rule_confidence),
                    ocr_confidence=None,
                    evidence_image_key=None,
                    evidence_clip_key=None,
                    geometry=geometry,
                    event_metadata=event_metadata,
                )

                await self.repository.create(event)

            else:
                event.camera_id = event.camera_id or camera_id

                event.event_metadata = event_metadata

                if geometry:
                    event.geometry = geometry

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

    async def persist_wrong_way_transitions(
        self,
        *,
        processing_job_id: UUID,
        video_id: UUID,
        camera_id: UUID | None,
        video_created_at: datetime,
        transitions: tuple[
            WrongWayTransition,
            ...,
        ],
        states: tuple[
            WrongWayViolationSnapshot,
            ...,
        ],
        tracks: tuple[TrackedObject, ...],
    ) -> tuple[ViolationEvent, ...]:
        """Create or update durable wrong-way events."""

        if not transitions:
            return ()

        states_by_key = {
            (
                state.track_id,
                state.lane_id,
            ): state
            for state in states
        }

        tracks_by_id = {track.track_id: track for track in tracks}

        persisted_events: list[ViolationEvent] = []

        for transition in transitions:
            event_key = self.build_wrong_way_event_key(
                processing_job_id=(processing_job_id),
                transition=transition,
            )

            event = await self.repository.get_by_event_key(
                event_key,
                for_update=True,
            )

            state = states_by_key.get(
                (
                    transition.track_id,
                    transition.lane_id,
                )
            )

            track = tracks_by_id.get(transition.track_id)

            detection_confidence = track.confidence if track is not None else None

            rule_confidence = float(
                min(
                    max(
                        (
                            state.opposition_score
                            if state is not None
                            else transition.opposition_score
                        ),
                        0.0,
                    ),
                    1.0,
                )
            )

            geometry = self._build_wrong_way_geometry(
                transition=transition,
                tracks_by_id=tracks_by_id,
            )

            existing_metadata = event.event_metadata if event is not None else {}

            event_metadata = self._merge_wrong_way_metadata(
                existing_metadata=(existing_metadata),
                transition=transition,
            )

            if event is None:
                occurred_at = self._calculate_wrong_way_occurred_at(
                    video_created_at=(video_created_at),
                    transition=transition,
                )

                event = ViolationEvent(
                    video_id=video_id,
                    camera_id=camera_id,
                    processing_job_id=(processing_job_id),
                    event_key=event_key,
                    violation_type=(ViolationType.WRONG_WAY),
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
                        (event.detection_confidence or 0.0),
                        detection_confidence,
                    )

                event.rule_confidence = max(
                    event.rule_confidence or 0.0,
                    rule_confidence,
                )

            persisted_events.append(event)

        await self.repository.commit()

        return tuple(persisted_events)

    async def attach_preview_to_job_events(
        self,
        *,
        processing_job_id: UUID,
        preview_key: str | None,
    ) -> int:
        """Attach the annotated preview to job violations."""

        if preview_key is None:
            return 0

        events = await self.repository.list_by_processing_job(
            processing_job_id,
            for_update=True,
        )

        changed_count = 0

        for event in events:
            if event.evidence_clip_key == preview_key:
                continue

            event.evidence_clip_key = preview_key
            changed_count += 1

        if events:
            await self.repository.commit()

        return changed_count

    @staticmethod
    def build_wrong_way_event_key(
        *,
        processing_job_id: UUID,
        transition: WrongWayTransition,
    ) -> str:
        """Build a stable wrong-way event key."""

        anchor_frame = transition.confirmed_frame or transition.first_candidate_frame

        return (
            f"wrong_way:{processing_job_id}:"
            f"{transition.track_id}:"
            f"{transition.lane_id}:"
            f"{anchor_frame}"
        )

    @staticmethod
    def build_triple_riding_event_key(
        *,
        processing_job_id: UUID,
        transition: TripleRidingTransition,
    ) -> str:
        """Build a stable key that survives worker retries."""

        anchor_frame = transition.confirmed_frame or transition.first_candidate_frame

        return (
            "triple_riding:"
            f"{processing_job_id}:"
            f"{transition.motorcycle_track_id}:"
            f"{anchor_frame}"
        )

    @staticmethod
    def build_no_helmet_event_key(
        *,
        processing_job_id: UUID,
        transition: NoHelmetTransition,
    ) -> str:
        """Build a stable key for a rider violation."""

        anchor_frame = transition.confirmed_frame or transition.first_candidate_frame

        return (
            f"no_helmet:{processing_job_id}:{transition.person_track_id}:{anchor_frame}"
        )

    @classmethod
    def _merge_wrong_way_metadata(
        cls,
        *,
        existing_metadata: dict[str, Any],
        transition: WrongWayTransition,
    ) -> dict[str, Any]:
        """Merge a wrong-way lifecycle transition."""

        metadata = dict(existing_metadata or {})

        history = [
            dict(entry)
            for entry in metadata.get(
                "transition_history",
                [],
            )
            if isinstance(entry, dict)
        ]

        transition_entry = {
            "type": (transition.transition_type.value),
            "frame_number": (transition.frame_number),
            "timestamp_seconds": (transition.timestamp_seconds),
            "track_id": (transition.track_id),
            "class_name": (transition.class_name),
            "lane_id": (transition.lane_id),
            "velocity": {
                "x": transition.velocity_x,
                "y": transition.velocity_y,
            },
            "speed_pixels_per_second": (transition.speed_pixels_per_second),
            "cosine_similarity": (transition.cosine_similarity),
            "opposition_score": (transition.opposition_score),
        }

        transition_identity = (
            transition_entry["type"],
            transition_entry["frame_number"],
        )

        already_recorded = any(
            (
                entry.get("type"),
                entry.get("frame_number"),
            )
            == transition_identity
            for entry in history
        )

        if not already_recorded:
            history.append(transition_entry)

        start_timestamp_seconds = max(
            transition.timestamp_seconds - transition.duration_seconds,
            0.0,
        )

        previous_peak = float(
            metadata.get(
                "peak_opposition_score",
                0.0,
            )
        )

        previous_minimum_cosine = float(
            metadata.get(
                "minimum_cosine_similarity",
                1.0,
            )
        )

        metadata.update(
            {
                "schema_version": "1.0",
                "track_id": (transition.track_id),
                "class_name": (transition.class_name),
                "lane_id": (transition.lane_id),
                "velocity": {
                    "x": (transition.velocity_x),
                    "y": (transition.velocity_y),
                },
                "speed_pixels_per_second": (transition.speed_pixels_per_second),
                "cosine_similarity": (transition.cosine_similarity),
                "opposition_score": (transition.opposition_score),
                "peak_opposition_score": max(
                    previous_peak,
                    transition.opposition_score,
                ),
                "minimum_cosine_similarity": min(
                    previous_minimum_cosine,
                    transition.cosine_similarity,
                ),
                "first_candidate_frame": (transition.first_candidate_frame),
                "confirmed_frame": (transition.confirmed_frame),
                "start_timestamp_seconds": (
                    metadata.get(
                        "start_timestamp_seconds",
                        start_timestamp_seconds,
                    )
                ),
                "last_transition_type": (transition.transition_type.value),
                "last_transition_frame": (transition.frame_number),
                "last_timestamp_seconds": (transition.timestamp_seconds),
                "transition_history": history,
            }
        )

        if transition.transition_type == WrongWayTransitionType.STARTED:
            if metadata.get("lifecycle_status") != "ended":
                metadata["lifecycle_status"] = "active"

            metadata.setdefault(
                "start_frame",
                transition.frame_number,
            )

            metadata.setdefault(
                "duration_seconds",
                0.0,
            )

        elif transition.transition_type == WrongWayTransitionType.ENDED:
            metadata.update(
                {
                    "lifecycle_status": ("ended"),
                    "end_frame": (transition.frame_number),
                    "end_timestamp_seconds": (transition.timestamp_seconds),
                    "duration_seconds": (transition.duration_seconds),
                }
            )

        return metadata

    @classmethod
    def _merge_metadata(
        cls,
        *,
        existing_metadata: dict[str, Any],
        transition: TripleRidingTransition,
    ) -> dict[str, Any]:
        metadata = dict(existing_metadata or {})

        history = [
            dict(entry)
            for entry in metadata.get(
                "transition_history",
                [],
            )
            if isinstance(entry, dict)
        ]

        transition_entry = {
            "type": (transition.transition_type.value),
            "frame_number": (transition.frame_number),
            "timestamp_seconds": (transition.timestamp_seconds),
            "rider_count": (transition.rider_count),
            "rider_track_ids": list(transition.rider_track_ids),
        }

        transition_identity = (
            transition_entry["type"],
            transition_entry["frame_number"],
        )

        history_contains_transition = any(
            (
                entry.get("type"),
                entry.get("frame_number"),
            )
            == transition_identity
            for entry in history
        )

        if not history_contains_transition:
            history.append(transition_entry)

        start_timestamp_seconds = max(
            transition.timestamp_seconds - transition.duration_seconds,
            0.0,
        )

        metadata.update(
            {
                "schema_version": "1.0",
                "motorcycle_track_id": (transition.motorcycle_track_id),
                "rider_track_ids": list(transition.rider_track_ids),
                "rider_count": (transition.rider_count),
                "peak_rider_count": max(
                    int(
                        metadata.get(
                            "peak_rider_count",
                            0,
                        )
                    ),
                    transition.peak_rider_count,
                ),
                "first_candidate_frame": (transition.first_candidate_frame),
                "confirmed_frame": (transition.confirmed_frame),
                "start_timestamp_seconds": (
                    metadata.get(
                        "start_timestamp_seconds",
                        start_timestamp_seconds,
                    )
                ),
                "last_transition_type": (transition.transition_type.value),
                "last_transition_frame": (transition.frame_number),
                "last_timestamp_seconds": (transition.timestamp_seconds),
                "transition_history": history,
            }
        )

        if transition.transition_type == TripleRidingTransitionType.STARTED:
            # A completed event should not be reopened when
            # the same job is replayed after a worker retry.
            if metadata.get("lifecycle_status") != "ended":
                metadata["lifecycle_status"] = "active"

            metadata.setdefault(
                "start_frame",
                transition.frame_number,
            )

            metadata.setdefault(
                "duration_seconds",
                0.0,
            )

        elif transition.transition_type == TripleRidingTransitionType.ENDED:
            metadata.update(
                {
                    "lifecycle_status": "ended",
                    "end_frame": (transition.frame_number),
                    "end_timestamp_seconds": (transition.timestamp_seconds),
                    "duration_seconds": (transition.duration_seconds),
                }
            )

        return metadata

    @classmethod
    def _merge_no_helmet_metadata(
        cls,
        *,
        existing_metadata: dict[str, Any],
        transition: NoHelmetTransition,
    ) -> dict[str, Any]:
        """Merge a no-helmet lifecycle transition."""

        metadata = dict(existing_metadata or {})

        history = [
            dict(entry)
            for entry in metadata.get(
                "transition_history",
                [],
            )
            if isinstance(entry, dict)
        ]

        transition_entry = {
            "type": (transition.transition_type.value),
            "frame_number": (transition.frame_number),
            "timestamp_seconds": (transition.timestamp_seconds),
            "detection_confidence": (transition.detection_confidence),
            "association_score": (transition.association_score),
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
                "schema_version": "1.0",
                "person_track_id": (transition.person_track_id),
                "motorcycle_track_id": (transition.motorcycle_track_id),
                "detection_confidence": (transition.detection_confidence),
                "association_score": (transition.association_score),
                "first_candidate_frame": (transition.first_candidate_frame),
                "confirmed_frame": (transition.confirmed_frame),
                "start_timestamp_seconds": (
                    metadata.get(
                        "start_timestamp_seconds",
                        start_timestamp_seconds,
                    )
                ),
                "last_transition_type": (transition.transition_type.value),
                "last_transition_frame": (transition.frame_number),
                "last_timestamp_seconds": (transition.timestamp_seconds),
                "transition_history": history,
            }
        )

        if transition.transition_type == NoHelmetTransitionType.STARTED:
            if metadata.get("lifecycle_status") != "ended":
                metadata["lifecycle_status"] = "active"

            metadata.setdefault(
                "start_frame",
                transition.frame_number,
            )

            metadata.setdefault(
                "duration_seconds",
                0.0,
            )

        elif transition.transition_type == NoHelmetTransitionType.ENDED:
            metadata.update(
                {
                    "lifecycle_status": "ended",
                    "end_frame": (transition.frame_number),
                    "end_timestamp_seconds": (transition.timestamp_seconds),
                    "duration_seconds": (transition.duration_seconds),
                }
            )

        return metadata

    @classmethod
    def _build_wrong_way_geometry(
        cls,
        *,
        transition: WrongWayTransition,
        tracks_by_id: dict[
            int,
            TrackedObject,
        ],
    ) -> dict[str, Any]:
        """Capture wrong-way track and motion geometry."""

        track = tracks_by_id.get(transition.track_id)

        geometry: dict[str, Any] = {
            "track_id": (transition.track_id),
            "class_name": (transition.class_name),
            "lane_id": (transition.lane_id),
            "velocity": {
                "x_pixels_per_second": (transition.velocity_x),
                "y_pixels_per_second": (transition.velocity_y),
            },
            "speed_pixels_per_second": (transition.speed_pixels_per_second),
            "cosine_similarity": (transition.cosine_similarity),
            "opposition_score": (transition.opposition_score),
        }

        if track is not None:
            geometry["vehicle"] = cls._serialize_track_geometry(track)

        return geometry

    @classmethod
    def _build_no_helmet_geometry(
        cls,
        *,
        transition: NoHelmetTransition,
        tracks_by_id: dict[
            int,
            TrackedObject,
        ],
    ) -> dict[str, Any]:
        """Capture rider and motorcycle geometry."""

        person = tracks_by_id.get(transition.person_track_id)

        motorcycle = tracks_by_id.get(transition.motorcycle_track_id)

        geometry: dict[str, Any] = {
            "person_track_id": (transition.person_track_id),
            "motorcycle_track_id": (transition.motorcycle_track_id),
        }

        if person is not None:
            geometry["person"] = cls._serialize_track_geometry(person)

        if motorcycle is not None:
            geometry["motorcycle"] = cls._serialize_track_geometry(motorcycle)

        return geometry

    @staticmethod
    def _calculate_wrong_way_occurred_at(
        *,
        video_created_at: datetime,
        transition: WrongWayTransition,
    ) -> datetime:
        """Convert a wrong-way video timestamp to UTC."""

        base_time = video_created_at

        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=timezone.utc)

        start_seconds = max(
            transition.timestamp_seconds - transition.duration_seconds,
            0.0,
        )

        return base_time + timedelta(seconds=start_seconds)

    @staticmethod
    def _calculate_occurred_at(
        *,
        video_created_at: datetime,
        transition: TripleRidingTransition,
    ) -> datetime:
        """Convert a video-relative timestamp to UTC time."""

        base_time = video_created_at

        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=timezone.utc)

        start_seconds = max(
            transition.timestamp_seconds - transition.duration_seconds,
            0.0,
        )

        return base_time + timedelta(seconds=start_seconds)

    @staticmethod
    def _rule_confidence(
        state: TripleRidingViolationSnapshot | None,
    ) -> float | None:
        if state is None:
            return None

        return float(
            min(
                max(
                    state.average_association_score,
                    0.0,
                ),
                1.0,
            )
        )

    @classmethod
    def _build_geometry(
        cls,
        *,
        transition: TripleRidingTransition,
        tracks_by_id: dict[
            int,
            TrackedObject,
        ],
    ) -> dict[str, Any]:
        motorcycle = tracks_by_id.get(transition.motorcycle_track_id)

        riders = [
            tracks_by_id[track_id]
            for track_id in transition.rider_track_ids
            if track_id in tracks_by_id
        ]

        geometry: dict[str, Any] = {
            "motorcycle_track_id": (transition.motorcycle_track_id),
            "rider_track_ids": list(transition.rider_track_ids),
        }

        if motorcycle is not None:
            geometry["motorcycle"] = cls._serialize_track_geometry(motorcycle)

        geometry["riders"] = [cls._serialize_track_geometry(rider) for rider in riders]

        return geometry

    @staticmethod
    def _serialize_track_geometry(
        track: TrackedObject,
    ) -> dict[str, Any]:
        box = track.bounding_box

        return {
            "track_id": track.track_id,
            "class_name": track.class_name,
            "bounding_box": {
                "x1": box.x1,
                "y1": box.y1,
                "x2": box.x2,
                "y2": box.y2,
                "width": box.width,
                "height": box.height,
                "center": list(box.center),
            },
        }

    async def attach_images_to_job_events(
        self,
        *,
        processing_job_id: UUID,
        evidence_keys: tuple[str, ...],
    ) -> int:
        """Attach the nearest evidence image to each violation."""

        if not evidence_keys:
            return 0

        events = await self.repository.list_by_processing_job(
            processing_job_id,
            for_update=True,
        )

        evidence_frames = [
            (
                key,
                self._extract_evidence_frame(key),
            )
            for key in evidence_keys
        ]

        evidence_frames = [
            (key, frame_number)
            for key, frame_number in evidence_frames
            if frame_number is not None
        ]

        changed_count = 0

        for event in events:
            if not evidence_frames:
                continue

            event_frame = event.frame_number or 0

            nearest_key, _ = min(
                evidence_frames,
                key=lambda item: abs(item[1] - event_frame),
            )

            if event.evidence_image_key == nearest_key:
                continue

            event.evidence_image_key = nearest_key
            changed_count += 1

        if events:
            await self.repository.commit()

        return changed_count

    @staticmethod
    def _extract_evidence_frame(
        key: str,
    ) -> int | None:
        match = re.search(
            r"frame-(\d+)\.(?:jpg|jpeg|png|webp)$",
            key,
            flags=re.IGNORECASE,
        )

        if match is None:
            return None

        return int(match.group(1))
