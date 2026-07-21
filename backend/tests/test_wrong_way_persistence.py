from datetime import (
    datetime,
    timezone,
)
from uuid import UUID, uuid4

import numpy as np
import pytest

from app.artifacts.traffic_video import (
    TrafficVideoArtifactWriter,
)
from app.detection.types import BoundingBox
from app.models.enums import ViolationType
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
)
from app.reasoning.wrong_way import (
    WrongWayTransition,
    WrongWayTransitionType,
    WrongWayViolationSnapshot,
)
from app.services.violation_event_lifecycle import (
    ViolationEventLifecycleService,
)
from app.tracking.types import TrackedObject


class FakeViolationEventRepository:
    """In-memory lifecycle repository."""

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

    async def create(
        self,
        event,
    ):
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
            if (event.processing_job_id == processing_job_id)
        ]

    async def commit(self) -> None:
        self.commit_count += 1


def create_track() -> TrackedObject:
    return TrackedObject(
        track_id=8,
        class_id=2,
        class_name="car",
        confidence=0.94,
        bounding_box=BoundingBox(
            x1=200,
            y1=100,
            x2=320,
            y2=240,
        ),
        age=8,
        hits=8,
        missed_frames=0,
        confirmed=True,
        velocity_x=0.0,
        velocity_y=80.0,
    )


def create_state() -> WrongWayViolationSnapshot:
    return WrongWayViolationSnapshot(
        track_id=8,
        class_name="car",
        lane_id="northbound",
        velocity_x=0.0,
        velocity_y=80.0,
        speed_pixels_per_second=80.0,
        cosine_similarity=-1.0,
        opposition_score=1.0,
        first_candidate_frame=2,
        confirmed_frame=4,
        last_violation_frame=4,
        consecutive_violation_frames=3,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )


def create_transition(
    *,
    transition_type: WrongWayTransitionType,
    frame_number: int,
    timestamp_seconds: float,
    duration_seconds: float,
) -> WrongWayTransition:
    return WrongWayTransition(
        transition_type=transition_type,
        track_id=8,
        class_name="car",
        lane_id="northbound",
        velocity_x=0.0,
        velocity_y=80.0,
        speed_pixels_per_second=80.0,
        cosine_similarity=-1.0,
        opposition_score=1.0,
        frame_number=frame_number,
        timestamp_seconds=(timestamp_seconds),
        first_candidate_frame=2,
        confirmed_frame=4,
        duration_seconds=(duration_seconds),
    )


@pytest.mark.asyncio
async def test_wrong_way_start_creates_event() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    events = await service.persist_wrong_way_transitions(
        processing_job_id=uuid4(),
        video_id=uuid4(),
        camera_id=uuid4(),
        video_created_at=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        transitions=(
            create_transition(
                transition_type=(WrongWayTransitionType.STARTED),
                frame_number=4,
                timestamp_seconds=0.3,
                duration_seconds=0.0,
            ),
        ),
        states=(create_state(),),
        tracks=(create_track(),),
    )

    assert len(events) == 1

    event = events[0]

    assert event.violation_type == ViolationType.WRONG_WAY

    assert event.track_id == "8"

    assert event.frame_number == 4

    assert event.rule_confidence == (pytest.approx(1.0))

    assert event.detection_confidence == (pytest.approx(0.94))

    assert event.event_metadata["lifecycle_status"] == "active"

    assert event.event_metadata["lane_id"] == "northbound"

    assert event.geometry["vehicle"]["bounding_box"]["x1"] == 200


@pytest.mark.asyncio
async def test_wrong_way_replay_is_idempotent_and_end_finalizes() -> None:
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
        "tracks": (create_track(),),
    }

    started = create_transition(
        transition_type=(WrongWayTransitionType.STARTED),
        frame_number=4,
        timestamp_seconds=0.3,
        duration_seconds=0.0,
    )

    await service.persist_wrong_way_transitions(
        **common,
        transitions=(started,),
        states=(create_state(),),
    )

    await service.persist_wrong_way_transitions(
        **common,
        transitions=(started,),
        states=(create_state(),),
    )

    assert len(repository.events) == 1

    event = next(iter(repository.events.values()))

    assert len(event.event_metadata["transition_history"]) == 1

    ended_events = await service.persist_wrong_way_transitions(
        **common,
        transitions=(
            create_transition(
                transition_type=(WrongWayTransitionType.ENDED),
                frame_number=12,
                timestamp_seconds=1.1,
                duration_seconds=0.8,
            ),
        ),
        states=(),
    )

    assert len(repository.events) == 1

    ended = ended_events[0]

    assert ended.event_metadata["lifecycle_status"] == "ended"

    assert ended.event_metadata["end_frame"] == 12

    assert ended.event_metadata["duration_seconds"] == pytest.approx(0.8)

    assert len(ended.event_metadata["transition_history"]) == 2


def test_wrong_way_start_forces_evidence_frame(
    tmp_path,
) -> None:
    job_id = uuid4()

    writer = TrafficVideoArtifactWriter(
        root=tmp_path,
        job_id=job_id,
        preview_fps=10.0,
        evidence_min_confidence=0.99,
        evidence_cooldown_frames=100,
        max_evidence_frames=3,
        preview_enabled=False,
    )

    frame = np.zeros(
        (
            360,
            640,
            3,
        ),
        dtype=np.uint8,
    )

    packet = FramePacket(
        frame_number=4,
        timestamp_seconds=0.3,
        image=frame,
    )

    analysis = FrameAnalysis(
        detections=(),
        wrong_way_states=(create_state(),),
        wrong_way_transitions=(
            create_transition(
                transition_type=(WrongWayTransitionType.STARTED),
                frame_number=4,
                timestamp_seconds=0.3,
                duration_seconds=0.0,
            ),
        ),
        annotated_frame=frame,
    )

    writer.write(
        packet=packet,
        analysis=analysis,
    )

    artifacts = writer.finish(
        pipeline_summary={
            "pipeline_version": "0.6.0",
        }
    )

    assert len(artifacts.evidence_keys) == 1

    evidence_path = tmp_path / str(job_id) / "evidence" / "frame-000004.jpg"

    assert evidence_path.exists()
