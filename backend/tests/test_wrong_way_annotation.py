import numpy as np

from app.detection.types import BoundingBox
from app.reasoning.wrong_way import (
    WrongWayViolationSnapshot,
)
from app.reasoning.wrong_way_annotation import (
    annotate_wrong_way,
)
from app.tracking.types import TrackedObject


def test_annotation_draws_confirmed_wrong_way() -> None:
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
            x1=200,
            y1=100,
            x2=320,
            y2=240,
        ),
        age=5,
        hits=5,
        missed_frames=0,
        confirmed=True,
        velocity_x=0.0,
        velocity_y=80.0,
    )

    violation = WrongWayViolationSnapshot(
        track_id=7,
        class_name="car",
        lane_id="northbound",
        velocity_x=0.0,
        velocity_y=80.0,
        speed_pixels_per_second=80.0,
        cosine_similarity=-1.0,
        opposition_score=1.0,
        first_candidate_frame=1,
        confirmed_frame=3,
        last_violation_frame=3,
        consecutive_violation_frames=3,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
    )

    annotated = annotate_wrong_way(
        frame,
        tracks=(track,),
        violations=(violation,),
    )

    assert annotated.shape == frame.shape
    assert np.any(annotated != frame)
