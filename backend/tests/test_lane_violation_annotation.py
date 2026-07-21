import numpy as np

from app.detection.types import BoundingBox
from app.reasoning.lane_violation import (
    LaneViolationSnapshot,
)
from app.reasoning.lane_violation_annotation import (
    annotate_lane_violations,
)
from app.tracking.types import TrackedObject


def test_draws_confirmed_lane_violation() -> None:
    frame = np.zeros(
        (
            360,
            640,
            3,
        ),
        dtype=np.uint8,
    )

    track = TrackedObject(
        track_id=7,
        class_id=2,
        class_name="car",
        confidence=0.95,
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

    violation = LaneViolationSnapshot(
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

    result = annotate_lane_violations(
        frame,
        tracks=(track,),
        violations=(violation,),
    )

    assert np.any(result != frame)
