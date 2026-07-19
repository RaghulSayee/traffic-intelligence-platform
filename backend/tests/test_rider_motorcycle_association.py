from app.detection.types import BoundingBox
from app.reasoning.rider_motorcycle import (
    RiderMotorcycleAssociator,
)
from app.tracking.types import TrackedObject


def create_track(
    *,
    track_id: int,
    class_id: int,
    class_name: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    velocity_x: float = 20.0,
    velocity_y: float = 0.0,
    confirmed: bool = True,
) -> TrackedObject:
    return TrackedObject(
        track_id=track_id,
        class_id=class_id,
        class_name=class_name,
        confidence=0.90,
        bounding_box=BoundingBox(
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
        ),
        age=5,
        hits=5,
        missed_frames=0,
        confirmed=confirmed,
        velocity_x=velocity_x,
        velocity_y=velocity_y,
    )


def create_associator(
    *,
    maximum_riders: int = 3,
) -> RiderMotorcycleAssociator:
    return RiderMotorcycleAssociator(
        minimum_score=0.55,
        max_riders_per_motorcycle=maximum_riders,
        max_anchor_distance_ratio=2.0,
        minimum_horizontal_overlap=0.05,
        minimum_motion_speed=5.0,
    )


def test_person_above_motorcycle_is_associated() -> None:
    associator = create_associator()

    person = create_track(
        track_id=1,
        class_id=0,
        class_name="person",
        x1=110,
        y1=40,
        x2=180,
        y2=190,
    )

    motorcycle = create_track(
        track_id=2,
        class_id=3,
        class_name="motorcycle",
        x1=90,
        y1=160,
        x2=220,
        y2=260,
    )

    result = associator.associate(
        (
            person,
            motorcycle,
        )
    )

    assert len(result.associations) == 1

    association = result.associations[0]

    assert association.person_track_id == 1
    assert association.motorcycle_track_id == 2
    assert association.score >= 0.55


def test_far_person_is_not_associated() -> None:
    associator = create_associator()

    person = create_track(
        track_id=1,
        class_id=0,
        class_name="person",
        x1=10,
        y1=40,
        x2=70,
        y2=180,
    )

    motorcycle = create_track(
        track_id=2,
        class_id=3,
        class_name="motorcycle",
        x1=500,
        y1=200,
        x2=650,
        y2=300,
    )

    result = associator.associate(
        (
            person,
            motorcycle,
        )
    )

    assert result.associations == ()
    assert result.unassigned_person_track_ids == (1,)


def test_person_is_assigned_to_best_motorcycle() -> None:
    associator = create_associator()

    person = create_track(
        track_id=1,
        class_id=0,
        class_name="person",
        x1=110,
        y1=40,
        x2=180,
        y2=190,
    )

    close_motorcycle = create_track(
        track_id=2,
        class_id=3,
        class_name="motorcycle",
        x1=90,
        y1=160,
        x2=220,
        y2=260,
    )

    distant_motorcycle = create_track(
        track_id=3,
        class_id=3,
        class_name="motorcycle",
        x1=290,
        y1=170,
        x2=430,
        y2=270,
    )

    result = associator.associate(
        (
            person,
            close_motorcycle,
            distant_motorcycle,
        )
    )

    assert len(result.associations) == 1

    assert result.associations[0].motorcycle_track_id == 2


def test_multiple_people_can_share_motorcycle() -> None:
    associator = create_associator(maximum_riders=3)

    first_person = create_track(
        track_id=1,
        class_id=0,
        class_name="person",
        x1=90,
        y1=40,
        x2=155,
        y2=190,
    )

    second_person = create_track(
        track_id=2,
        class_id=0,
        class_name="person",
        x1=145,
        y1=45,
        x2=210,
        y2=190,
    )

    motorcycle = create_track(
        track_id=3,
        class_id=3,
        class_name="motorcycle",
        x1=80,
        y1=160,
        x2=225,
        y2=265,
    )

    result = associator.associate(
        (
            first_person,
            second_person,
            motorcycle,
        )
    )

    assert len(result.associations) == 2

    assert {association.person_track_id for association in result.associations} == {
        1,
        2,
    }

    assert result.rider_counts_by_motorcycle() == {
        3: 2,
    }


def test_motorcycle_capacity_is_respected() -> None:
    associator = create_associator(maximum_riders=2)

    people = tuple(
        create_track(
            track_id=track_id,
            class_id=0,
            class_name="person",
            x1=80 + track_id * 15,
            y1=40,
            x2=145 + track_id * 15,
            y2=190,
        )
        for track_id in (
            1,
            2,
            3,
        )
    )

    motorcycle = create_track(
        track_id=10,
        class_id=3,
        class_name="motorcycle",
        x1=70,
        y1=160,
        x2=240,
        y2=270,
    )

    result = associator.associate(
        (
            *people,
            motorcycle,
        )
    )

    assert len(result.associations) == 2
    assert len(result.unassigned_person_track_ids) == 1


def test_unconfirmed_tracks_are_ignored() -> None:
    associator = create_associator()

    person = create_track(
        track_id=1,
        class_id=0,
        class_name="person",
        x1=110,
        y1=40,
        x2=180,
        y2=190,
        confirmed=False,
    )

    motorcycle = create_track(
        track_id=2,
        class_id=3,
        class_name="motorcycle",
        x1=90,
        y1=160,
        x2=220,
        y2=260,
    )

    result = associator.associate(
        (
            person,
            motorcycle,
        )
    )

    assert result.associations == ()
    assert result.unassigned_person_track_ids == ()
