from app.detection.types import (
    BoundingBox,
    Detection,
)
from app.reasoning.helmet_rider import (
    HelmetRiderAssociator,
)
from app.reasoning.rider_motorcycle import (
    RiderAssociationFeatures,
)
from app.reasoning.temporal_rider import (
    TemporalRiderAssociation,
)
from app.tracking.types import TrackedObject


def create_person_track(
    *,
    track_id: int = 1,
) -> TrackedObject:
    return TrackedObject(
        track_id=track_id,
        class_id=0,
        class_name="person",
        confidence=0.95,
        bounding_box=BoundingBox(
            x1=100,
            y1=40,
            x2=160,
            y2=220,
        ),
        age=5,
        hits=5,
        missed_frames=0,
        confirmed=True,
        velocity_x=0.0,
        velocity_y=0.0,
    )


def create_rider_association(
    *,
    person_track_id: int = 1,
) -> TemporalRiderAssociation:
    return TemporalRiderAssociation(
        person_track_id=person_track_id,
        motorcycle_track_id=10,
        latest_score=0.90,
        smoothed_score=0.88,
        consecutive_matches=3,
        total_matches=3,
        missed_frames=0,
        confirmed=True,
        observed_this_frame=True,
        features=RiderAssociationFeatures(
            horizontal_overlap_score=0.9,
            anchor_distance_score=0.9,
            vertical_position_score=0.9,
            motion_similarity_score=0.9,
            containment_score=0.9,
        ),
    )


def create_detection(
    *,
    class_name: str,
    confidence: float,
) -> Detection:
    return Detection(
        class_id=0,
        class_name=class_name,
        confidence=confidence,
        bounding_box=BoundingBox(
            x1=112,
            y1=45,
            x2=148,
            y2=100,
        ),
        model_name="fake-helmet-model",
    )


def create_associator() -> HelmetRiderAssociator:
    return HelmetRiderAssociator(
        head_height_ratio=0.35,
        head_width_expansion_ratio=0.10,
        minimum_score=0.45,
    )


def test_associates_no_helmet_with_rider() -> None:
    result = create_associator().associate(
        tracks=(create_person_track(),),
        rider_associations=(create_rider_association(),),
        helmet_detections=(
            create_detection(
                class_name="no_helmet",
                confidence=0.92,
            ),
        ),
    )

    assert len(result.associations) == 1

    association = result.associations[0]

    assert association.person_track_id == 1
    assert association.motorcycle_track_id == 10
    assert association.class_name == "no_helmet"
    assert association.detection_confidence == 0.92


def test_ignores_person_without_rider_relationship() -> None:
    result = create_associator().associate(
        tracks=(create_person_track(),),
        rider_associations=(),
        helmet_detections=(
            create_detection(
                class_name="no_helmet",
                confidence=0.92,
            ),
        ),
    )

    assert result.associations == ()
    assert result.unassigned_detection_indexes == (0,)


def test_conflicting_labels_choose_stronger_detection() -> None:
    result = create_associator().associate(
        tracks=(create_person_track(),),
        rider_associations=(create_rider_association(),),
        helmet_detections=(
            create_detection(
                class_name="helmet",
                confidence=0.60,
            ),
            create_detection(
                class_name="no_helmet",
                confidence=0.95,
            ),
        ),
    )

    assert len(result.associations) == 1

    assert result.associations[0].class_name == "no_helmet"
