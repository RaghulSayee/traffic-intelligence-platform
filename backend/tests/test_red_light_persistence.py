from datetime import (
    datetime,
    timezone,
)
from uuid import uuid4

import numpy as np
import pytest

from app.artifacts.traffic_video import (
    TrafficVideoArtifactWriter,
)
from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
)
from app.models.enums import (
    ReviewStatus,
    ViolationType,
)
from app.reasoning.red_light import (
    RedLightTransitionType,
    RedLightViolationTransition,
)
from app.reasoning.traffic_light_state import (
    TrafficLightState,
)
from app.services.violation_event_lifecycle import (
    ViolationEventLifecycleService,
)


class FakeViolationEventRepository:
    """In-memory repository used for lifecycle tests."""

    def __init__(self) -> None:
        self.events_by_key = {}
        self.commit_count = 0

    async def get_by_event_key(
        self,
        event_key: str,
        *,
        for_update: bool = False,
    ):
        del for_update

        return self.events_by_key.get(event_key)

    async def create(
        self,
        event,
    ):
        self.events_by_key[event.event_key] = event

        return event

    async def list_by_processing_job(
        self,
        processing_job_id,
        *,
        for_update: bool = False,
    ):
        del for_update

        return [
            event
            for event in self.events_by_key.values()
            if event.processing_job_id == processing_job_id
        ]

    async def commit(self) -> None:
        self.commit_count += 1


def create_transition(
    *,
    frame_number: int = 10,
    timestamp_seconds: float = 0.90,
    rule_confidence: float = 0.95,
) -> RedLightViolationTransition:
    return RedLightViolationTransition(
        transition_type=(RedLightTransitionType.STARTED),
        track_id=7,
        class_name="car",
        stop_line_id="stop-1",
        lane_id="lane-1",
        traffic_light_region_id=("signal-1"),
        signal_state=(TrafficLightState.RED),
        signal_confidence=0.96,
        previous_frame_number=(frame_number - 1),
        frame_number=frame_number,
        timestamp_seconds=(timestamp_seconds),
        previous_anchor_x_normalized=0.50,
        previous_anchor_y_normalized=0.40,
        anchor_x_normalized=0.50,
        anchor_y_normalized=0.60,
        previous_signed_distance_pixels=(-10.0),
        signed_distance_pixels=10.0,
        crossing_depth_pixels=20.0,
        velocity_x=0.0,
        velocity_y=100.0,
        speed_pixels_per_second=100.0,
        direction_cosine=1.0,
        detection_confidence=0.90,
        rule_confidence=(rule_confidence),
    )


@pytest.mark.asyncio
async def test_persists_red_light_violation() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    processing_job_id = uuid4()
    video_id = uuid4()
    camera_id = uuid4()

    created_at = datetime(
        2026,
        7,
        21,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    events = await service.persist_red_light_transitions(
        processing_job_id=(processing_job_id),
        video_id=video_id,
        camera_id=camera_id,
        video_created_at=(created_at),
        transitions=(create_transition(),),
    )

    assert len(events) == 1

    event = events[0]

    assert event.violation_type == ViolationType.RED_LIGHT

    assert event.review_status == ReviewStatus.PENDING

    assert event.frame_number == 10
    assert event.track_id == "7"

    assert event.detection_confidence == pytest.approx(0.90)

    assert event.rule_confidence == pytest.approx(0.95)

    assert event.occurred_at == created_at.replace(microsecond=900000)

    assert event.geometry["stop_line_id"] == "stop-1"

    assert event.geometry["traffic_light_region_id"] == "signal-1"

    assert event.event_metadata["signal_state"] == "red"

    assert len(event.event_metadata["transition_history"]) == 1

    assert repository.commit_count == 1


@pytest.mark.asyncio
async def test_replaying_transition_is_idempotent() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    processing_job_id = uuid4()
    video_id = uuid4()

    transition = create_transition()

    keyword_arguments = {
        "processing_job_id": (processing_job_id),
        "video_id": video_id,
        "camera_id": None,
        "video_created_at": datetime(
            2026,
            7,
            21,
            tzinfo=timezone.utc,
        ),
        "transitions": (transition,),
    }

    first = await service.persist_red_light_transitions(**keyword_arguments)

    second = await service.persist_red_light_transitions(**keyword_arguments)

    assert len(first) == 1
    assert len(second) == 1

    assert first[0] is second[0]

    assert len(repository.events_by_key) == 1

    assert len(second[0].event_metadata["transition_history"]) == 1

    assert repository.commit_count == 2


@pytest.mark.asyncio
async def test_distinct_crossings_create_distinct_events() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    processing_job_id = uuid4()

    events = await service.persist_red_light_transitions(
        processing_job_id=(processing_job_id),
        video_id=uuid4(),
        camera_id=None,
        video_created_at=datetime(
            2026,
            7,
            21,
            tzinfo=timezone.utc,
        ),
        transitions=(
            create_transition(
                frame_number=10,
                timestamp_seconds=0.90,
            ),
            create_transition(
                frame_number=20,
                timestamp_seconds=1.90,
            ),
        ),
    )

    assert len(events) == 2

    assert len(repository.events_by_key) == 2

    assert events[0].event_key != events[1].event_key


@pytest.mark.asyncio
async def test_empty_transitions_do_not_commit() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    events = await service.persist_red_light_transitions(
        processing_job_id=uuid4(),
        video_id=uuid4(),
        camera_id=None,
        video_created_at=datetime(
            2026,
            7,
            21,
            tzinfo=timezone.utc,
        ),
        transitions=(),
    )

    assert events == ()
    assert repository.commit_count == 0


@pytest.mark.asyncio
async def test_attaches_nearest_evidence_image_to_red_light_event() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    processing_job_id = uuid4()

    events = await service.persist_red_light_transitions(
        processing_job_id=(processing_job_id),
        video_id=uuid4(),
        camera_id=None,
        video_created_at=datetime(
            2026,
            7,
            21,
            tzinfo=timezone.utc,
        ),
        transitions=(
            create_transition(
                frame_number=10,
                timestamp_seconds=0.90,
            ),
        ),
    )

    evidence_keys = (
        (f"{processing_job_id}/evidence/frame-000004.jpg"),
        (f"{processing_job_id}/evidence/frame-000010.jpg"),
        (f"{processing_job_id}/evidence/frame-000020.jpg"),
    )

    changed = await service.attach_images_to_job_events(
        processing_job_id=(processing_job_id),
        evidence_keys=evidence_keys,
    )

    assert changed == 1

    assert events[0].evidence_image_key == evidence_keys[1]


@pytest.mark.asyncio
async def test_attaching_same_evidence_is_idempotent() -> None:
    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    processing_job_id = uuid4()

    events = await service.persist_red_light_transitions(
        processing_job_id=(processing_job_id),
        video_id=uuid4(),
        camera_id=None,
        video_created_at=datetime(
            2026,
            7,
            21,
            tzinfo=timezone.utc,
        ),
        transitions=(create_transition(),),
    )

    evidence_key = f"{processing_job_id}/evidence/frame-000010.jpg"

    first_changed = await service.attach_images_to_job_events(
        processing_job_id=(processing_job_id),
        evidence_keys=(evidence_key,),
    )

    second_changed = await service.attach_images_to_job_events(
        processing_job_id=(processing_job_id),
        evidence_keys=(evidence_key,),
    )

    assert first_changed == 1
    assert second_changed == 0

    assert events[0].evidence_image_key == evidence_key


def test_red_light_transition_forces_evidence_capture(
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
            200,
            200,
            3,
        ),
        dtype=np.uint8,
    )

    packet = FramePacket(
        frame_number=10,
        timestamp_seconds=0.90,
        image=frame,
    )

    analysis = FrameAnalysis(
        red_light_transitions=(create_transition(),),
        annotated_frame=frame.copy(),
    )

    writer.write(
        packet=packet,
        analysis=analysis,
    )

    artifact_summary = writer.finish(
        pipeline_summary={
            "pipeline_name": ("yolo-traffic-pipeline"),
            "pipeline_version": "1.0.0",
        }
    )

    expected_key = f"{job_id}/evidence/frame-000010.jpg"

    expected_path = tmp_path / str(job_id) / "evidence" / "frame-000010.jpg"

    assert artifact_summary.evidence_keys == (expected_key,)

    assert expected_path.exists()
    assert expected_path.stat().st_size > 0
