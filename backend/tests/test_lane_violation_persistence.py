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
from app.models.enums import (
    ReviewStatus,
    ViolationType,
)
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
)
from app.reasoning.lane_violation import (
    LaneViolationSnapshot,
    LaneViolationTransition,
    LaneViolationTransitionType,
)
from app.services.violation_event_lifecycle import (
    ViolationEventLifecycleService,
)
from app.tracking.types import TrackedObject


class FakeViolationEventRepository:
    """In-memory event repository."""

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


def create_state() -> LaneViolationSnapshot:
    return LaneViolationSnapshot(
        track_id=7,
        class_name="car",
        nearest_lane_id="lane-1",
        anchor_x_normalized=0.75,
        anchor_y_normalized=0.60,
        distance_to_nearest_lane_pixels=50.0,
        velocity_x=80.0,
        velocity_y=0.0,
        speed_pixels_per_second=80.0,
        first_candidate_frame=1,
        confirmed_frame=3,
        last_violation_frame=3,
        consecutive_violation_frames=3,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )


def create_transition(
    *,
    transition_type: (LaneViolationTransitionType),
    frame_number: int,
    timestamp_seconds: float,
    duration_seconds: float,
) -> LaneViolationTransition:
    return LaneViolationTransition(
        transition_type=transition_type,
        track_id=7,
        class_name="car",
        nearest_lane_id="lane-1",
        anchor_x_normalized=0.75,
        anchor_y_normalized=0.60,
        distance_to_nearest_lane_pixels=50.0,
        velocity_x=80.0,
        velocity_y=0.0,
        speed_pixels_per_second=80.0,
        frame_number=frame_number,
        timestamp_seconds=(timestamp_seconds),
        first_candidate_frame=1,
        confirmed_frame=3,
        duration_seconds=(duration_seconds),
    )


def create_track() -> TrackedObject:
    return TrackedObject(
        track_id=7,
        class_id=2,
        class_name="car",
        confidence=0.91,
        bounding_box=BoundingBox(
            x1=420,
            y1=100,
            x2=540,
            y2=230,
        ),
        age=5,
        hits=5,
        missed_frames=0,
        confirmed=True,
        velocity_x=80.0,
        velocity_y=0.0,
    )


@pytest.mark.asyncio
async def test_started_lane_transition_creates_event() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    job_id = uuid4()

    events = await service.persist_lane_violation_transitions(
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
                transition_type=(LaneViolationTransitionType.STARTED),
                frame_number=3,
                timestamp_seconds=0.2,
                duration_seconds=0.0,
            ),
        ),
        states=(create_state(),),
        tracks=(create_track(),),
    )

    assert len(events) == 1
    assert len(repository.events) == 1

    event = events[0]

    assert event.violation_type == ViolationType.LANE_VIOLATION

    assert event.review_status == ReviewStatus.PENDING

    assert event.track_id == "7"

    assert event.detection_confidence == pytest.approx(0.91)

    assert event.event_metadata["lifecycle_status"] == "active"

    assert event.geometry["nearest_lane_id"] == "lane-1"


@pytest.mark.asyncio
async def test_replay_and_end_are_idempotent() -> None:
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
        transition_type=(LaneViolationTransitionType.STARTED),
        frame_number=3,
        timestamp_seconds=0.2,
        duration_seconds=0.0,
    )

    await service.persist_lane_violation_transitions(
        **common,
        transitions=(started,),
        states=(create_state(),),
    )

    await service.persist_lane_violation_transitions(
        **common,
        transitions=(started,),
        states=(create_state(),),
    )

    ended = create_transition(
        transition_type=(LaneViolationTransitionType.ENDED),
        frame_number=10,
        timestamp_seconds=0.9,
        duration_seconds=0.7,
    )

    events = await service.persist_lane_violation_transitions(
        **common,
        transitions=(ended,),
        states=(),
    )

    assert len(repository.events) == 1

    event = events[0]

    assert event.event_metadata["lifecycle_status"] == "ended"

    assert event.event_metadata["end_frame"] == 10

    assert event.event_metadata["duration_seconds"] == pytest.approx(0.7)

    assert len(event.event_metadata["transition_history"]) == 2


def test_lane_start_forces_evidence(
    tmp_path,
) -> None:
    job_id = uuid4()

    writer = TrafficVideoArtifactWriter(
        root=tmp_path,
        job_id=job_id,
        preview_fps=10.0,
        evidence_min_confidence=1.0,
        evidence_cooldown_frames=100,
        max_evidence_frames=5,
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

    transition = create_transition(
        transition_type=(LaneViolationTransitionType.STARTED),
        frame_number=3,
        timestamp_seconds=0.2,
        duration_seconds=0.0,
    )

    writer.write(
        packet=FramePacket(
            frame_number=3,
            timestamp_seconds=0.2,
            image=frame,
        ),
        analysis=FrameAnalysis(
            lane_violation_transitions=(transition,),
            annotated_frame=frame,
        ),
    )

    summary = writer.finish(
        pipeline_summary={
            "pipeline_version": "0.7.0",
        }
    )

    assert len(summary.evidence_keys) == 1

    assert summary.evidence_keys[0].endswith("/evidence/frame-000003.jpg")
