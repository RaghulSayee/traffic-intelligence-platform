import cv2

from app.pipelines.base import VideoFrame
from app.reasoning.temporal_rider import (
    TemporalRiderAssociation,
)
from app.reasoning.triple_riding import (
    TripleRidingViolationSnapshot,
)
from app.tracking.types import TrackedObject


def annotate_reasoning(
    frame: VideoFrame,
    *,
    tracks: tuple[TrackedObject, ...],
    associations: tuple[
        TemporalRiderAssociation,
        ...,
    ],
    violations: tuple[
        TripleRidingViolationSnapshot,
        ...,
    ],
) -> VideoFrame:
    """Draw rider relationships and triple-riding warnings."""

    annotated = frame.copy()

    image_height, image_width = annotated.shape[:2]

    tracks_by_id = {track.track_id: track for track in tracks}

    violating_motorcycle_ids = {
        violation.motorcycle_track_id for violation in violations if violation.confirmed
    }

    for association in associations:
        if not association.confirmed:
            continue

        person = tracks_by_id.get(association.person_track_id)

        motorcycle = tracks_by_id.get(association.motorcycle_track_id)

        if person is None or motorcycle is None:
            continue

        person_center = tuple(int(value) for value in person.bounding_box.center)

        motorcycle_center = tuple(
            int(value) for value in motorcycle.bounding_box.center
        )

        motorcycle_is_violating = motorcycle.track_id in violating_motorcycle_ids

        line_color = (0, 0, 255) if motorcycle_is_violating else (0, 165, 255)

        cv2.line(
            annotated,
            person_center,
            motorcycle_center,
            line_color,
            thickness=2,
            lineType=cv2.LINE_AA,
        )

        midpoint = (
            int((person_center[0] + motorcycle_center[0]) / 2),
            int((person_center[1] + motorcycle_center[1]) / 2),
        )

        cv2.putText(
            annotated,
            f"rider {association.smoothed_score:.2f}",
            midpoint,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            line_color,
            thickness=2,
            lineType=cv2.LINE_AA,
        )

    for violation in violations:
        if not violation.confirmed:
            continue

        motorcycle = tracks_by_id.get(violation.motorcycle_track_id)

        if motorcycle is None:
            continue

        box = motorcycle.bounding_box.clipped(
            image_width=image_width,
            image_height=image_height,
        )

        x1, y1, x2, y2 = box.as_integer_tuple()

        cv2.rectangle(
            annotated,
            (x1, y1),
            (x2, y2),
            (0, 0, 255),
            thickness=4,
        )

        label = f"TRIPLE RIDING ({violation.rider_count} riders)"

        text_size, baseline = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            2,
        )

        text_width, text_height = text_size

        text_top = max(
            y1 - text_height - baseline - 10,
            0,
        )

        cv2.rectangle(
            annotated,
            (x1, text_top),
            (
                min(
                    x1 + text_width + 10,
                    image_width,
                ),
                y1,
            ),
            (0, 0, 255),
            thickness=-1,
        )

        cv2.putText(
            annotated,
            label,
            (
                x1 + 5,
                max(
                    y1 - 6,
                    text_height,
                ),
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            thickness=2,
            lineType=cv2.LINE_AA,
        )

    return annotated
