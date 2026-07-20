from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.models.enums import ViolationType
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
from app.services.violation_event_lifecycle import (
    ViolationEventLifecycleService,
)


class FakeViolationEventRepository:
    """In-memory repository for lifecycle tests."""

    def __init__(self) -> None:
        self.events = {}
        self.commit_count = 0

    async def get_by_event_key(
        self,
        event_key: str,
        *,
        for_update: bool = False,
    ):
        return self.events.get(event_key)

    async def create(self, event):
        self.events[event.event_key] = event
        return event

    async def list_by_processing_job(
        self,
        processing_job_id: UUID,
        *,
        for_update: bool = False,
    ):
        return [
            event
            for event in self.events.values()
            if event.processing_job_id == processing_job_id
        ]

    async def commit(self) -> None:
        self.commit_count += 1


def create_transition(
    *,
    transition_type: (TripleRidingTransitionType),
    frame_number: int,
    timestamp_seconds: float,
    duration_seconds: float,
) -> TripleRidingTransition:
    return TripleRidingTransition(
        transition_type=transition_type,
        motorcycle_track_id=10,
        rider_track_ids=(1, 2, 3),
        rider_count=3,
        peak_rider_count=3,
        frame_number=frame_number,
        timestamp_seconds=timestamp_seconds,
        first_candidate_frame=1,
        confirmed_frame=3,
        duration_seconds=duration_seconds,
    )


def create_state() -> TripleRidingViolationSnapshot:
    return TripleRidingViolationSnapshot(
        motorcycle_track_id=10,
        rider_track_ids=(1, 2, 3),
        rider_count=3,
        peak_rider_count=3,
        average_association_score=0.87,
        first_candidate_frame=1,
        confirmed_frame=3,
        last_violation_frame=3,
        consecutive_violation_frames=3,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )


@pytest.mark.asyncio
async def test_started_transition_creates_event() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    job_id = uuid4()

    events = await service.persist_triple_riding_transitions(
        processing_job_id=job_id,
        video_id=uuid4(),
        camera_id=None,
        video_created_at=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        transitions=(
            create_transition(
                transition_type=(TripleRidingTransitionType.STARTED),
                frame_number=3,
                timestamp_seconds=0.4,
                duration_seconds=0.0,
            ),
        ),
        states=(create_state(),),
        tracks=(),
    )

    assert len(events) == 1
    assert len(repository.events) == 1

    event = events[0]

    assert event.event_metadata["lifecycle_status"] == "active"

    assert event.rule_confidence == 0.87
    assert event.track_id == "10"


@pytest.mark.asyncio
async def test_replayed_start_does_not_duplicate_event() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    job_id = uuid4()
    video_id = uuid4()

    arguments = {
        "processing_job_id": job_id,
        "video_id": video_id,
        "camera_id": None,
        "video_created_at": datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        "transitions": (
            create_transition(
                transition_type=(TripleRidingTransitionType.STARTED),
                frame_number=3,
                timestamp_seconds=0.4,
                duration_seconds=0.0,
            ),
        ),
        "states": (create_state(),),
        "tracks": (),
    }

    await service.persist_triple_riding_transitions(**arguments)

    await service.persist_triple_riding_transitions(**arguments)

    assert len(repository.events) == 1

    event = next(iter(repository.events.values()))

    assert len(event.event_metadata["transition_history"]) == 1


@pytest.mark.asyncio
async def test_ended_transition_finalizes_existing_event() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    job_id = uuid4()
    video_id = uuid4()

    common_arguments = {
        "processing_job_id": job_id,
        "video_id": video_id,
        "camera_id": None,
        "video_created_at": datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        "tracks": (),
    }

    await service.persist_triple_riding_transitions(
        **common_arguments,
        transitions=(
            create_transition(
                transition_type=(TripleRidingTransitionType.STARTED),
                frame_number=3,
                timestamp_seconds=0.4,
                duration_seconds=0.0,
            ),
        ),
        states=(create_state(),),
    )

    events = await service.persist_triple_riding_transitions(
        **common_arguments,
        transitions=(
            create_transition(
                transition_type=(TripleRidingTransitionType.ENDED),
                frame_number=20,
                timestamp_seconds=2.0,
                duration_seconds=1.6,
            ),
        ),
        states=(),
    )

    assert len(repository.events) == 1

    event = events[0]
    metadata = event.event_metadata

    assert metadata["lifecycle_status"] == "ended"
    assert metadata["end_frame"] == 20
    assert metadata["duration_seconds"] == 1.6

    assert len(metadata["transition_history"]) == 2


@pytest.mark.asyncio
async def test_preview_is_attached_to_job_events() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    job_id = uuid4()

    await service.persist_triple_riding_transitions(
        processing_job_id=job_id,
        video_id=uuid4(),
        camera_id=None,
        video_created_at=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        transitions=(
            create_transition(
                transition_type=(TripleRidingTransitionType.STARTED),
                frame_number=3,
                timestamp_seconds=0.4,
                duration_seconds=0.0,
            ),
        ),
        states=(create_state(),),
        tracks=(),
    )

    changed = await service.attach_preview_to_job_events(
        processing_job_id=job_id,
        preview_key=(f"{job_id}/annotated-preview.mp4"),
    )

    event = next(iter(repository.events.values()))

    assert changed == 1

    assert event.evidence_clip_key == (f"{job_id}/annotated-preview.mp4")


def create_no_helmet_transition(
    *,
    transition_type: NoHelmetTransitionType,
    frame_number: int,
    timestamp_seconds: float,
    duration_seconds: float,
) -> NoHelmetTransition:
    return NoHelmetTransition(
        transition_type=transition_type,
        person_track_id=1,
        motorcycle_track_id=10,
        detection_confidence=0.91,
        association_score=0.86,
        frame_number=frame_number,
        timestamp_seconds=timestamp_seconds,
        first_candidate_frame=1,
        confirmed_frame=3,
        duration_seconds=duration_seconds,
    )


def create_no_helmet_state() -> NoHelmetViolationSnapshot:
    return NoHelmetViolationSnapshot(
        person_track_id=1,
        motorcycle_track_id=10,
        detection_confidence=0.91,
        association_score=0.86,
        first_candidate_frame=1,
        confirmed_frame=3,
        last_violation_frame=3,
        consecutive_violation_frames=3,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )


@pytest.mark.asyncio
async def test_no_helmet_start_creates_event() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    events = await service.persist_no_helmet_transitions(
        processing_job_id=uuid4(),
        video_id=uuid4(),
        camera_id=None,
        video_created_at=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        transitions=(
            create_no_helmet_transition(
                transition_type=(NoHelmetTransitionType.STARTED),
                frame_number=3,
                timestamp_seconds=0.2,
                duration_seconds=0.0,
            ),
        ),
        states=(create_no_helmet_state(),),
        tracks=(),
    )

    assert len(events) == 1
    assert len(repository.events) == 1

    event = events[0]

    assert event.violation_type == ViolationType.NO_HELMET

    assert event.track_id == "1"

    assert event.detection_confidence == 0.91
    assert event.rule_confidence == 0.86

    assert event.event_metadata["lifecycle_status"] == "active"


@pytest.mark.asyncio
async def test_no_helmet_replay_does_not_duplicate() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    job_id = uuid4()
    video_id = uuid4()

    arguments = {
        "processing_job_id": job_id,
        "video_id": video_id,
        "camera_id": None,
        "video_created_at": datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        "transitions": (
            create_no_helmet_transition(
                transition_type=(NoHelmetTransitionType.STARTED),
                frame_number=3,
                timestamp_seconds=0.2,
                duration_seconds=0.0,
            ),
        ),
        "states": (create_no_helmet_state(),),
        "tracks": (),
    }

    await service.persist_no_helmet_transitions(**arguments)

    await service.persist_no_helmet_transitions(**arguments)

    assert len(repository.events) == 1

    event = next(iter(repository.events.values()))

    assert len(event.event_metadata["transition_history"]) == 1


@pytest.mark.asyncio
async def test_no_helmet_end_finalizes_event() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    job_id = uuid4()
    video_id = uuid4()

    common = {
        "processing_job_id": job_id,
        "video_id": video_id,
        "camera_id": None,
        "video_created_at": datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        "tracks": (),
    }

    await service.persist_no_helmet_transitions(
        **common,
        transitions=(
            create_no_helmet_transition(
                transition_type=(NoHelmetTransitionType.STARTED),
                frame_number=3,
                timestamp_seconds=0.2,
                duration_seconds=0.0,
            ),
        ),
        states=(create_no_helmet_state(),),
    )

    events = await service.persist_no_helmet_transitions(
        **common,
        transitions=(
            create_no_helmet_transition(
                transition_type=(NoHelmetTransitionType.ENDED),
                frame_number=20,
                timestamp_seconds=2.0,
                duration_seconds=1.8,
            ),
        ),
        states=(),
    )

    assert len(repository.events) == 1

    metadata = events[0].event_metadata

    assert metadata["lifecycle_status"] == "ended"

    assert metadata["end_frame"] == 20

    assert metadata["duration_seconds"] == 1.8

    assert len(metadata["transition_history"]) == 2
