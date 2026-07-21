import pytest

from app.reasoning.traffic_light_state import (
    TrafficLightObservation,
    TrafficLightState,
    TrafficLightStateResult,
)
from app.reasoning.traffic_light_temporal import (
    TrafficLightTemporalStabilizer,
)


def observation(
    state: TrafficLightState,
    *,
    confidence: float = 0.90,
) -> TrafficLightObservation:
    scores = {
        TrafficLightState.RED: (
            0.20,
            0.0,
            0.0,
        ),
        TrafficLightState.YELLOW: (
            0.0,
            0.20,
            0.0,
        ),
        TrafficLightState.GREEN: (
            0.0,
            0.0,
            0.20,
        ),
        TrafficLightState.UNKNOWN: (
            0.0,
            0.0,
            0.0,
        ),
    }

    red_score, yellow_score, green_score = scores[state]

    return TrafficLightObservation(
        region_id="signal-1",
        region_name="Main Signal",
        state=state,
        confidence=(confidence if state != TrafficLightState.UNKNOWN else 0.0),
        red_score=red_score,
        yellow_score=yellow_score,
        green_score=green_score,
        active_pixel_ratio=(red_score + yellow_score + green_score),
        polygon_pixel_count=1000,
        active_pixel_count=(200 if state != TrafficLightState.UNKNOWN else 0),
    )


def result(
    state: TrafficLightState,
    *,
    confidence: float = 0.90,
) -> TrafficLightStateResult:
    return TrafficLightStateResult(
        observations=(
            observation(
                state,
                confidence=confidence,
            ),
        )
    )


def create_stabilizer(
    *,
    confirmation_frames: int = 3,
    maximum_unknown_frames: int = 2,
) -> TrafficLightTemporalStabilizer:
    return TrafficLightTemporalStabilizer(
        confirmation_frames=(confirmation_frames),
        maximum_unknown_frames=(maximum_unknown_frames),
        confidence_alpha=0.40,
    )


def update(
    stabilizer: TrafficLightTemporalStabilizer,
    *,
    frame_number: int,
    state: TrafficLightState,
):
    return stabilizer.update(
        frame_number=frame_number,
        timestamp_seconds=((frame_number - 1) * 0.1),
        observations=result(state),
    )


def test_confirms_initial_red_after_required_frames() -> None:
    stabilizer = create_stabilizer(confirmation_frames=3)

    first = update(
        stabilizer,
        frame_number=1,
        state=TrafficLightState.RED,
    )

    second = update(
        stabilizer,
        frame_number=2,
        state=TrafficLightState.RED,
    )

    third = update(
        stabilizer,
        frame_number=3,
        state=TrafficLightState.RED,
    )

    assert first.states[0].stable_state == TrafficLightState.UNKNOWN

    assert second.states[0].consecutive_candidate_frames == 2

    assert third.states[0].stable_state == TrafficLightState.RED

    assert len(third.transitions) == 1

    transition = third.transitions[0]

    assert transition.previous_state == TrafficLightState.UNKNOWN

    assert transition.current_state == TrafficLightState.RED

    assert transition.frame_number == 3


def test_single_green_flicker_does_not_replace_red() -> None:
    stabilizer = create_stabilizer(confirmation_frames=2)

    update(
        stabilizer,
        frame_number=1,
        state=TrafficLightState.RED,
    )

    update(
        stabilizer,
        frame_number=2,
        state=TrafficLightState.RED,
    )

    flicker = update(
        stabilizer,
        frame_number=3,
        state=TrafficLightState.GREEN,
    )

    assert flicker.states[0].stable_state == TrafficLightState.RED

    assert flicker.states[0].candidate_state == TrafficLightState.GREEN

    assert flicker.transitions == ()


def test_sustained_green_replaces_red() -> None:
    stabilizer = create_stabilizer(confirmation_frames=2)

    update(
        stabilizer,
        frame_number=1,
        state=TrafficLightState.RED,
    )

    update(
        stabilizer,
        frame_number=2,
        state=TrafficLightState.RED,
    )

    update(
        stabilizer,
        frame_number=3,
        state=TrafficLightState.GREEN,
    )

    changed = update(
        stabilizer,
        frame_number=4,
        state=TrafficLightState.GREEN,
    )

    assert changed.states[0].stable_state == TrafficLightState.GREEN

    assert len(changed.transitions) == 1

    assert changed.transitions[0].previous_state == TrafficLightState.RED

    assert changed.transitions[0].current_state == TrafficLightState.GREEN


def test_brief_unknown_gap_preserves_stable_state() -> None:
    stabilizer = create_stabilizer(
        confirmation_frames=1,
        maximum_unknown_frames=2,
    )

    update(
        stabilizer,
        frame_number=1,
        state=TrafficLightState.RED,
    )

    first_unknown = update(
        stabilizer,
        frame_number=2,
        state=TrafficLightState.UNKNOWN,
    )

    second_unknown = update(
        stabilizer,
        frame_number=3,
        state=TrafficLightState.UNKNOWN,
    )

    assert first_unknown.states[0].stable_state == TrafficLightState.RED

    assert second_unknown.states[0].stable_state == TrafficLightState.RED

    assert second_unknown.transitions == ()


def test_long_unknown_gap_changes_state_to_unknown() -> None:
    stabilizer = create_stabilizer(
        confirmation_frames=1,
        maximum_unknown_frames=2,
    )

    update(
        stabilizer,
        frame_number=1,
        state=TrafficLightState.RED,
    )

    update(
        stabilizer,
        frame_number=2,
        state=TrafficLightState.UNKNOWN,
    )

    update(
        stabilizer,
        frame_number=3,
        state=TrafficLightState.UNKNOWN,
    )

    changed = update(
        stabilizer,
        frame_number=4,
        state=TrafficLightState.UNKNOWN,
    )

    assert changed.states[0].stable_state == TrafficLightState.UNKNOWN

    assert len(changed.transitions) == 1

    transition = changed.transitions[0]

    assert transition.previous_state == TrafficLightState.RED

    assert transition.current_state == TrafficLightState.UNKNOWN


def test_missing_region_counts_as_unknown() -> None:
    stabilizer = create_stabilizer(
        confirmation_frames=1,
        maximum_unknown_frames=0,
    )

    update(
        stabilizer,
        frame_number=1,
        state=TrafficLightState.RED,
    )

    missing = stabilizer.update(
        frame_number=2,
        timestamp_seconds=0.1,
        observations=(TrafficLightStateResult(observations=())),
    )

    assert missing.states[0].stable_state == TrafficLightState.UNKNOWN

    assert missing.states[0].observed_this_frame is False

    assert len(missing.transitions) == 1


def test_same_stable_state_smooths_confidence() -> None:
    stabilizer = create_stabilizer(confirmation_frames=1)

    first = stabilizer.update(
        frame_number=1,
        timestamp_seconds=0.0,
        observations=result(
            TrafficLightState.RED,
            confidence=0.80,
        ),
    )

    second = stabilizer.update(
        frame_number=2,
        timestamp_seconds=0.1,
        observations=result(
            TrafficLightState.RED,
            confidence=1.0,
        ),
    )

    assert first.states[0].stable_confidence == pytest.approx(0.80)

    assert second.states[0].stable_confidence == pytest.approx(0.88)


def test_reset_clears_previous_state() -> None:
    stabilizer = create_stabilizer(confirmation_frames=1)

    update(
        stabilizer,
        frame_number=1,
        state=TrafficLightState.RED,
    )

    stabilizer.reset()

    empty = stabilizer.update(
        frame_number=2,
        timestamp_seconds=0.1,
        observations=TrafficLightStateResult(observations=()),
    )

    assert empty.states == ()
    assert empty.transitions == ()


@pytest.mark.parametrize(
    "keyword_arguments",
    [
        {
            "confirmation_frames": 0,
            "maximum_unknown_frames": 2,
            "confidence_alpha": 0.40,
        },
        {
            "confirmation_frames": 3,
            "maximum_unknown_frames": -1,
            "confidence_alpha": 0.40,
        },
        {
            "confirmation_frames": 3,
            "maximum_unknown_frames": 2,
            "confidence_alpha": 0.0,
        },
        {
            "confirmation_frames": 3,
            "maximum_unknown_frames": 2,
            "confidence_alpha": 1.1,
        },
    ],
)
def test_rejects_invalid_configuration(
    keyword_arguments,
) -> None:
    with pytest.raises(ValueError):
        TrafficLightTemporalStabilizer(**keyword_arguments)
