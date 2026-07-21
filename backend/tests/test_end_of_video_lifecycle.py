from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.models.enums import ViolationType
from app.pipelines.yolo_traffic import (
    YoloTrafficPipeline,
)
from app.reasoning.lane_violation import (
    LaneViolationDetector,
    LaneViolationTransitionType,
    _LaneViolationState,
)
from app.reasoning.no_helmet import (
    NoHelmetTransitionType,
    NoHelmetViolationDetector,
    _NoHelmetState,
)
from app.reasoning.triple_riding import (
    TripleRidingTransitionType,
    TripleRidingViolationDetector,
    _TripleRidingState,
)
from app.reasoning.wrong_way import (
    WrongWayTransitionType,
    WrongWayViolationDetector,
    _WrongWayState,
)
from app.services.violation_event_lifecycle import (
    ViolationEventLifecycleService,
)


class FakeViolationEventRepository:
    """In-memory event repository for finalization tests."""

    def __init__(self) -> None:
        self.events = {}
        self.commit_count = 0

    async def get_by_event_key(
        self,
        event_key: str,
        *,
        for_update: bool = False,
    ):
        del for_update

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
        del for_update

        return [
            event
            for event in self.events.values()
            if event.processing_job_id == processing_job_id
        ]

    async def commit(self) -> None:
        self.commit_count += 1


def create_triple_riding_state() -> _TripleRidingState:
    return _TripleRidingState(
        motorcycle_track_id=10,
        rider_track_ids=(1, 2, 3),
        rider_count=3,
        peak_rider_count=3,
        average_association_score=0.88,
        first_candidate_frame=1,
        first_candidate_timestamp=0.0,
        confirmed_frame=3,
        confirmed_timestamp=0.2,
        last_violation_frame=10,
        last_violation_timestamp=0.9,
        consecutive_violation_frames=10,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )


def create_no_helmet_state() -> _NoHelmetState:
    return _NoHelmetState(
        person_track_id=1,
        motorcycle_track_id=10,
        detection_confidence=0.91,
        association_score=0.87,
        first_candidate_frame=1,
        first_candidate_timestamp=0.0,
        confirmed_frame=3,
        confirmed_timestamp=0.2,
        last_violation_frame=10,
        last_violation_timestamp=0.9,
        consecutive_violation_frames=10,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )


def create_wrong_way_state() -> _WrongWayState:
    return _WrongWayState(
        track_id=20,
        class_name="car",
        lane_id="lane-1",
        velocity_x=0.0,
        velocity_y=-120.0,
        speed_pixels_per_second=120.0,
        cosine_similarity=-1.0,
        opposition_score=1.0,
        first_candidate_frame=1,
        first_candidate_timestamp=0.0,
        confirmed_frame=3,
        confirmed_timestamp=0.2,
        last_violation_frame=10,
        last_violation_timestamp=0.9,
        consecutive_violation_frames=10,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )


def create_lane_violation_state() -> _LaneViolationState:
    return _LaneViolationState(
        track_id=30,
        class_name="car",
        nearest_lane_id="lane-1",
        anchor_x_normalized=0.95,
        anchor_y_normalized=0.60,
        distance_to_nearest_lane_pixels=25.0,
        velocity_x=0.0,
        velocity_y=90.0,
        speed_pixels_per_second=90.0,
        first_candidate_frame=1,
        first_candidate_timestamp=0.0,
        confirmed_frame=3,
        confirmed_timestamp=0.2,
        last_violation_frame=10,
        last_violation_timestamp=0.9,
        consecutive_violation_frames=10,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )


def create_pipeline_with_active_states():
    triple_state = create_triple_riding_state()

    no_helmet_state = create_no_helmet_state()

    wrong_way_state = create_wrong_way_state()

    lane_state = create_lane_violation_state()

    triple_detector = object.__new__(TripleRidingViolationDetector)

    triple_detector._states = {triple_state.motorcycle_track_id: (triple_state)}

    no_helmet_detector = object.__new__(NoHelmetViolationDetector)

    no_helmet_detector._states = {no_helmet_state.person_track_id: (no_helmet_state)}

    wrong_way_detector = object.__new__(WrongWayViolationDetector)

    wrong_way_detector._states = {
        (
            wrong_way_state.track_id,
            wrong_way_state.lane_id,
        ): wrong_way_state
    }

    lane_detector = object.__new__(LaneViolationDetector)

    lane_detector._states = {lane_state.track_id: lane_state}

    pipeline = object.__new__(YoloTrafficPipeline)

    pipeline.last_frame_number = 10
    pipeline.last_timestamp_seconds = 0.9

    pipeline.triple_riding_detector = triple_detector

    pipeline.no_helmet_detector = no_helmet_detector

    pipeline.wrong_way_detector = wrong_way_detector

    pipeline.lane_violation_detector = lane_detector

    return (
        pipeline,
        triple_state,
        no_helmet_state,
        wrong_way_state,
        lane_state,
    )


async def persist_started_events(
    *,
    service: ViolationEventLifecycleService,
    processing_job_id,
    video_id,
    video_created_at,
    triple_state,
    no_helmet_state,
    wrong_way_state,
    lane_state,
) -> None:
    triple_started = TripleRidingViolationDetector._create_transition(
        state=triple_state,
        transition_type=(TripleRidingTransitionType.STARTED),
        frame_number=3,
        timestamp_seconds=0.2,
    )

    no_helmet_started = NoHelmetViolationDetector._create_transition(
        state=no_helmet_state,
        transition_type=(NoHelmetTransitionType.STARTED),
        frame_number=3,
        timestamp_seconds=0.2,
    )

    wrong_way_started = WrongWayViolationDetector._create_transition(
        state=wrong_way_state,
        transition_type=(WrongWayTransitionType.STARTED),
        frame_number=3,
        timestamp_seconds=0.2,
    )

    lane_started = LaneViolationDetector._create_transition(
        state=lane_state,
        transition_type=(LaneViolationTransitionType.STARTED),
        frame_number=3,
        timestamp_seconds=0.2,
    )

    await service.persist_triple_riding_transitions(
        processing_job_id=processing_job_id,
        video_id=video_id,
        camera_id=None,
        video_created_at=video_created_at,
        transitions=(triple_started,),
        states=(triple_state.to_public(),),
        tracks=(),
    )

    await service.persist_no_helmet_transitions(
        processing_job_id=processing_job_id,
        video_id=video_id,
        camera_id=None,
        video_created_at=video_created_at,
        transitions=(no_helmet_started,),
        states=(no_helmet_state.to_public(),),
        tracks=(),
    )

    await service.persist_wrong_way_transitions(
        processing_job_id=processing_job_id,
        video_id=video_id,
        camera_id=None,
        video_created_at=video_created_at,
        transitions=(wrong_way_started,),
        states=(wrong_way_state.to_public(),),
        tracks=(),
    )

    await service.persist_lane_violation_transitions(
        processing_job_id=processing_job_id,
        video_id=video_id,
        camera_id=None,
        video_created_at=video_created_at,
        transitions=(lane_started,),
        states=(lane_state.to_public(),),
        tracks=(),
    )


async def persist_final_analysis(
    *,
    service: ViolationEventLifecycleService,
    processing_job_id,
    video_id,
    video_created_at,
    final_analysis,
) -> None:
    await service.persist_triple_riding_transitions(
        processing_job_id=processing_job_id,
        video_id=video_id,
        camera_id=None,
        video_created_at=video_created_at,
        transitions=(final_analysis.triple_riding_transitions),
        states=(final_analysis.triple_riding_states),
        tracks=final_analysis.tracks,
    )

    await service.persist_no_helmet_transitions(
        processing_job_id=processing_job_id,
        video_id=video_id,
        camera_id=None,
        video_created_at=video_created_at,
        transitions=(final_analysis.no_helmet_transitions),
        states=(final_analysis.no_helmet_states),
        tracks=final_analysis.tracks,
    )

    await service.persist_wrong_way_transitions(
        processing_job_id=processing_job_id,
        video_id=video_id,
        camera_id=None,
        video_created_at=video_created_at,
        transitions=(final_analysis.wrong_way_transitions),
        states=(final_analysis.wrong_way_states),
        tracks=final_analysis.tracks,
    )

    await service.persist_lane_violation_transitions(
        processing_job_id=processing_job_id,
        video_id=video_id,
        camera_id=None,
        video_created_at=video_created_at,
        transitions=(final_analysis.lane_violation_transitions),
        states=(final_analysis.lane_violation_states),
        tracks=final_analysis.tracks,
    )


@pytest.mark.asyncio
async def test_end_of_video_finalizes_all_active_events() -> None:
    (
        pipeline,
        triple_state,
        no_helmet_state,
        wrong_way_state,
        lane_state,
    ) = create_pipeline_with_active_states()

    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    processing_job_id = uuid4()
    video_id = uuid4()

    video_created_at = datetime(
        2026,
        7,
        21,
        12,
        0,
        tzinfo=timezone.utc,
    )

    await persist_started_events(
        service=service,
        processing_job_id=(processing_job_id),
        video_id=video_id,
        video_created_at=(video_created_at),
        triple_state=triple_state,
        no_helmet_state=no_helmet_state,
        wrong_way_state=wrong_way_state,
        lane_state=lane_state,
    )

    assert len(repository.events) == 4

    for event in repository.events.values():
        assert event.event_metadata["lifecycle_status"] == "active"

    final_analysis = pipeline._finalize_active_violations()

    assert final_analysis is not None

    assert len(final_analysis.triple_riding_transitions) == 1

    assert len(final_analysis.no_helmet_transitions) == 1

    assert len(final_analysis.wrong_way_transitions) == 1

    assert len(final_analysis.lane_violation_transitions) == 1

    await persist_final_analysis(
        service=service,
        processing_job_id=(processing_job_id),
        video_id=video_id,
        video_created_at=(video_created_at),
        final_analysis=final_analysis,
    )

    assert len(repository.events) == 4

    event_types = {event.violation_type for event in repository.events.values()}

    assert event_types == {
        ViolationType.TRIPLE_RIDING,
        ViolationType.NO_HELMET,
        ViolationType.WRONG_WAY,
        ViolationType.LANE_VIOLATION,
    }

    for event in repository.events.values():
        metadata = event.event_metadata

        assert metadata["lifecycle_status"] == "ended"

        assert metadata["end_frame"] == 10

        assert metadata["end_timestamp_seconds"] == pytest.approx(0.9)

        assert metadata["duration_seconds"] == pytest.approx(0.7)

        assert len(metadata["transition_history"]) == 2


@pytest.mark.asyncio
async def test_final_transition_replay_is_idempotent() -> None:
    (
        pipeline,
        triple_state,
        no_helmet_state,
        wrong_way_state,
        lane_state,
    ) = create_pipeline_with_active_states()

    repository = FakeViolationEventRepository()

    service = ViolationEventLifecycleService(repository=repository)

    processing_job_id = uuid4()
    video_id = uuid4()

    video_created_at = datetime(
        2026,
        7,
        21,
        tzinfo=timezone.utc,
    )

    await persist_started_events(
        service=service,
        processing_job_id=(processing_job_id),
        video_id=video_id,
        video_created_at=(video_created_at),
        triple_state=triple_state,
        no_helmet_state=no_helmet_state,
        wrong_way_state=wrong_way_state,
        lane_state=lane_state,
    )

    final_analysis = pipeline._finalize_active_violations()

    assert final_analysis is not None

    await persist_final_analysis(
        service=service,
        processing_job_id=(processing_job_id),
        video_id=video_id,
        video_created_at=(video_created_at),
        final_analysis=final_analysis,
    )

    await persist_final_analysis(
        service=service,
        processing_job_id=(processing_job_id),
        video_id=video_id,
        video_created_at=(video_created_at),
        final_analysis=final_analysis,
    )

    assert len(repository.events) == 4

    for event in repository.events.values():
        assert event.event_metadata["lifecycle_status"] == "ended"

        assert len(event.event_metadata["transition_history"]) == 2


def test_second_pipeline_finalization_is_empty() -> None:
    (
        pipeline,
        _,
        _,
        _,
        _,
    ) = create_pipeline_with_active_states()

    first = pipeline._finalize_active_violations()

    second = pipeline._finalize_active_violations()

    assert first is not None
    assert second is None
