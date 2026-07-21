import pytest

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


def test_flushes_confirmed_triple_riding_state() -> None:
    detector = object.__new__(TripleRidingViolationDetector)

    detector._states = {
        10: _TripleRidingState(
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
        ),
        20: _TripleRidingState(
            motorcycle_track_id=20,
            rider_track_ids=(4, 5, 6),
            rider_count=3,
            peak_rider_count=3,
            average_association_score=0.70,
            first_candidate_frame=10,
            first_candidate_timestamp=0.9,
            confirmed_frame=None,
            confirmed_timestamp=None,
            last_violation_frame=10,
            last_violation_timestamp=0.9,
            consecutive_violation_frames=1,
            missed_frames=0,
            confirmed=False,
            observed_this_frame=True,
        ),
    }

    transitions = detector.flush(
        frame_number=12,
        timestamp_seconds=1.1,
    )

    assert len(transitions) == 1

    transition = transitions[0]

    assert transition.transition_type == TripleRidingTransitionType.ENDED

    assert transition.motorcycle_track_id == 10
    assert transition.frame_number == 12

    assert transition.duration_seconds == pytest.approx(0.9)

    assert detector._states == {}

    assert (
        detector.flush(
            frame_number=12,
            timestamp_seconds=1.1,
        )
        == ()
    )


def test_flushes_confirmed_no_helmet_state() -> None:
    detector = object.__new__(NoHelmetViolationDetector)

    detector._states = {
        1: _NoHelmetState(
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
        ),
        2: _NoHelmetState(
            person_track_id=2,
            motorcycle_track_id=20,
            detection_confidence=0.60,
            association_score=0.65,
            first_candidate_frame=10,
            first_candidate_timestamp=0.9,
            confirmed_frame=None,
            confirmed_timestamp=None,
            last_violation_frame=10,
            last_violation_timestamp=0.9,
            consecutive_violation_frames=1,
            missed_frames=0,
            confirmed=False,
            observed_this_frame=True,
        ),
    }

    transitions = detector.flush(
        frame_number=12,
        timestamp_seconds=1.1,
    )

    assert len(transitions) == 1

    transition = transitions[0]

    assert transition.transition_type == NoHelmetTransitionType.ENDED

    assert transition.person_track_id == 1
    assert transition.frame_number == 12

    assert transition.duration_seconds == pytest.approx(0.9)

    assert detector._states == {}


def test_flushes_confirmed_wrong_way_state() -> None:
    detector = object.__new__(WrongWayViolationDetector)

    detector._states = {
        (7, "lane-1"): _WrongWayState(
            track_id=7,
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
        ),
        (8, "lane-1"): _WrongWayState(
            track_id=8,
            class_name="car",
            lane_id="lane-1",
            velocity_x=0.0,
            velocity_y=-60.0,
            speed_pixels_per_second=60.0,
            cosine_similarity=-0.8,
            opposition_score=0.8,
            first_candidate_frame=10,
            first_candidate_timestamp=0.9,
            confirmed_frame=None,
            confirmed_timestamp=None,
            last_violation_frame=10,
            last_violation_timestamp=0.9,
            consecutive_violation_frames=1,
            missed_frames=0,
            confirmed=False,
            observed_this_frame=True,
        ),
    }

    transitions = detector.flush(
        frame_number=12,
        timestamp_seconds=1.1,
    )

    assert len(transitions) == 1

    transition = transitions[0]

    assert transition.transition_type == WrongWayTransitionType.ENDED

    assert transition.track_id == 7
    assert transition.lane_id == "lane-1"

    assert transition.duration_seconds == pytest.approx(0.9)

    assert detector._states == {}


def test_flushes_confirmed_lane_violation_state() -> None:
    detector = object.__new__(LaneViolationDetector)

    detector._states = {
        15: _LaneViolationState(
            track_id=15,
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
        ),
        16: _LaneViolationState(
            track_id=16,
            class_name="car",
            nearest_lane_id="lane-1",
            anchor_x_normalized=0.94,
            anchor_y_normalized=0.65,
            distance_to_nearest_lane_pixels=20.0,
            velocity_x=0.0,
            velocity_y=70.0,
            speed_pixels_per_second=70.0,
            first_candidate_frame=10,
            first_candidate_timestamp=0.9,
            confirmed_frame=None,
            confirmed_timestamp=None,
            last_violation_frame=10,
            last_violation_timestamp=0.9,
            consecutive_violation_frames=1,
            missed_frames=0,
            confirmed=False,
            observed_this_frame=True,
        ),
    }

    transitions = detector.flush(
        frame_number=12,
        timestamp_seconds=1.1,
    )

    assert len(transitions) == 1

    transition = transitions[0]

    assert transition.transition_type == LaneViolationTransitionType.ENDED

    assert transition.track_id == 15

    assert transition.duration_seconds == pytest.approx(0.9)

    assert detector._states == {}


@pytest.mark.parametrize(
    "detector_class",
    [
        TripleRidingViolationDetector,
        NoHelmetViolationDetector,
        WrongWayViolationDetector,
        LaneViolationDetector,
    ],
)
def test_flush_rejects_invalid_frame_number(
    detector_class,
) -> None:
    detector = object.__new__(detector_class)

    detector._states = {}

    with pytest.raises(
        ValueError,
        match="Frame number",
    ):
        detector.flush(
            frame_number=0,
            timestamp_seconds=0.0,
        )


@pytest.mark.parametrize(
    "detector_class",
    [
        TripleRidingViolationDetector,
        NoHelmetViolationDetector,
        WrongWayViolationDetector,
        LaneViolationDetector,
    ],
)
def test_flush_rejects_negative_timestamp(
    detector_class,
) -> None:
    detector = object.__new__(detector_class)

    detector._states = {}

    with pytest.raises(
        ValueError,
        match="Timestamp",
    ):
        detector.flush(
            frame_number=1,
            timestamp_seconds=-0.1,
        )
