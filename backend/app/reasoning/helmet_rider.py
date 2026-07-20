from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from app.detection.helmet import (
    HELMET_CLASS_NAME,
    NO_HELMET_CLASS_NAME,
    SUPPORTED_HELMET_CLASSES,
)
from app.detection.types import (
    BoundingBox,
    Detection,
)
from app.reasoning.temporal_rider import (
    TemporalRiderAssociation,
)
from app.tracking.types import TrackedObject


@dataclass(frozen=True, slots=True)
class HelmetRiderAssociation:
    """A helmet-related detection assigned to one rider."""

    person_track_id: int
    motorcycle_track_id: int

    class_name: str

    detection_confidence: float
    association_score: float

    head_region: BoundingBox
    detection_box: BoundingBox


@dataclass(frozen=True, slots=True)
class HelmetRiderAssociationResult:
    """Helmet-to-rider associations produced for one frame."""

    associations: tuple[
        HelmetRiderAssociation,
        ...,
    ]

    unassigned_detection_indexes: tuple[int, ...] = ()

    def association_for_person(
        self,
        person_track_id: int,
    ) -> HelmetRiderAssociation | None:
        """Return the helmet result assigned to one person."""

        return next(
            (
                association
                for association in self.associations
                if association.person_track_id == person_track_id
            ),
            None,
        )

    @property
    def no_helmet_associations(
        self,
    ) -> tuple[HelmetRiderAssociation, ...]:
        """Return associations classified as no-helmet."""

        return tuple(
            association
            for association in self.associations
            if association.class_name == NO_HELMET_CLASS_NAME
        )

    @property
    def helmet_associations(
        self,
    ) -> tuple[HelmetRiderAssociation, ...]:
        """Return associations classified as helmet."""

        return tuple(
            association
            for association in self.associations
            if association.class_name == HELMET_CLASS_NAME
        )


@dataclass(frozen=True, slots=True)
class _CandidateAssociation:
    """Internal scored detection-to-rider candidate."""

    detection_index: int
    person_track_id: int
    motorcycle_track_id: int

    class_name: str

    detection_confidence: float
    association_score: float

    head_region: BoundingBox
    detection_box: BoundingBox


class HelmetRiderAssociator:
    """
    Associate helmet detections with confirmed motorcycle riders.

    The upper portion of the rider's person box is treated as the
    estimated head region. Each detection and rider can be assigned
    at most once.
    """

    def __init__(
        self,
        *,
        head_height_ratio: float,
        head_width_expansion_ratio: float,
        minimum_score: float,
    ) -> None:
        if not 0.0 < head_height_ratio <= 1.0:
            raise ValueError(
                "Head height ratio must be greater than zero and no greater than one."
            )

        if head_width_expansion_ratio < 0.0:
            raise ValueError("Head width expansion ratio cannot be negative.")

        if not 0.0 <= minimum_score <= 1.0:
            raise ValueError("Minimum association score must be between zero and one.")

        self.head_height_ratio = head_height_ratio

        self.head_width_expansion_ratio = head_width_expansion_ratio

        self.minimum_score = minimum_score

    def associate(
        self,
        *,
        tracks: tuple[TrackedObject, ...],
        rider_associations: tuple[
            TemporalRiderAssociation,
            ...,
        ],
        helmet_detections: tuple[
            Detection,
            ...,
        ],
    ) -> HelmetRiderAssociationResult:
        """Assign helmet-related detections to confirmed riders."""

        tracks_by_id = {track.track_id: track for track in tracks}

        riders: list[
            tuple[
                TemporalRiderAssociation,
                TrackedObject,
            ]
        ] = []

        for rider_association in rider_associations:
            if (
                not rider_association.confirmed
                or not rider_association.observed_this_frame
            ):
                continue

            person = tracks_by_id.get(rider_association.person_track_id)

            if (
                person is None
                or not person.confirmed
                or person.missed_frames != 0
                or person.class_name != "person"
            ):
                continue

            riders.append(
                (
                    rider_association,
                    person,
                )
            )

        relevant_detections = [
            (
                detection_index,
                detection,
            )
            for detection_index, detection in enumerate(helmet_detections)
            if detection.class_name in SUPPORTED_HELMET_CLASSES
        ]

        if not riders or not relevant_detections:
            return HelmetRiderAssociationResult(
                associations=(),
                unassigned_detection_indexes=tuple(
                    detection_index for detection_index, _ in relevant_detections
                ),
            )

        candidates: list[_CandidateAssociation] = []

        for (
            rider_association,
            person,
        ) in riders:
            head_region = self.estimate_head_region(person.bounding_box)

            for (
                detection_index,
                detection,
            ) in relevant_detections:
                score = self._association_score(
                    head_region=head_region,
                    detection=detection,
                )

                if score is None:
                    continue

                candidates.append(
                    _CandidateAssociation(
                        detection_index=detection_index,
                        person_track_id=(rider_association.person_track_id),
                        motorcycle_track_id=(rider_association.motorcycle_track_id),
                        class_name=(detection.class_name),
                        detection_confidence=(detection.confidence),
                        association_score=score,
                        head_region=head_region,
                        detection_box=(detection.bounding_box),
                    )
                )

        candidates.sort(
            key=lambda candidate: (
                -candidate.association_score,
                -candidate.detection_confidence,
                candidate.person_track_id,
                candidate.detection_index,
            )
        )

        assigned_people: set[int] = set()
        assigned_detections: set[int] = set()

        associations: list[HelmetRiderAssociation] = []

        for candidate in candidates:
            if (
                candidate.person_track_id in assigned_people
                or candidate.detection_index in assigned_detections
            ):
                continue

            assigned_people.add(candidate.person_track_id)

            assigned_detections.add(candidate.detection_index)

            associations.append(
                HelmetRiderAssociation(
                    person_track_id=(candidate.person_track_id),
                    motorcycle_track_id=(candidate.motorcycle_track_id),
                    class_name=candidate.class_name,
                    detection_confidence=(candidate.detection_confidence),
                    association_score=(candidate.association_score),
                    head_region=(candidate.head_region),
                    detection_box=(candidate.detection_box),
                )
            )

        associations.sort(
            key=lambda association: (
                association.motorcycle_track_id,
                association.person_track_id,
            )
        )

        unassigned_detection_indexes = tuple(
            detection_index
            for detection_index, _ in relevant_detections
            if detection_index not in assigned_detections
        )

        return HelmetRiderAssociationResult(
            associations=tuple(associations),
            unassigned_detection_indexes=(unassigned_detection_indexes),
        )

    def estimate_head_region(
        self,
        person_box: BoundingBox,
    ) -> BoundingBox:
        """Estimate a rider head region from a person box."""

        head_height = person_box.height * self.head_height_ratio

        horizontal_expansion = person_box.width * self.head_width_expansion_ratio

        return BoundingBox(
            x1=(person_box.x1 - horizontal_expansion),
            y1=person_box.y1,
            x2=(person_box.x2 + horizontal_expansion),
            y2=(person_box.y1 + head_height),
        )

    def _association_score(
        self,
        *,
        head_region: BoundingBox,
        detection: Detection,
    ) -> float | None:
        detection_box = detection.bounding_box

        containment_score = self._intersection_area(
            head_region,
            detection_box,
        ) / max(
            detection_box.area,
            1.0,
        )

        head_center_x, head_center_y = head_region.center

        detection_center_x, detection_center_y = detection_box.center

        center_distance = hypot(
            detection_center_x - head_center_x,
            detection_center_y - head_center_y,
        )

        normalization_distance = max(
            hypot(
                head_region.width,
                head_region.height,
            ),
            1.0,
        )

        center_score = self._clamp01(1.0 - center_distance / normalization_distance)

        detection_center_inside = (
            head_region.x1 <= detection_center_x <= head_region.x2
            and head_region.y1 <= detection_center_y <= head_region.y2
        )

        if not detection_center_inside and containment_score < 0.20:
            return None

        score = (
            0.50 * containment_score + 0.25 * center_score + 0.25 * detection.confidence
        )

        score = self._clamp01(score)

        if score < self.minimum_score:
            return None

        return score

    @staticmethod
    def _intersection_area(
        first: BoundingBox,
        second: BoundingBox,
    ) -> float:
        intersection_width = max(
            min(first.x2, second.x2) - max(first.x1, second.x1),
            0.0,
        )

        intersection_height = max(
            min(first.y2, second.y2) - max(first.y1, second.y1),
            0.0,
        )

        return intersection_width * intersection_height

    @staticmethod
    def _clamp01(
        value: float,
    ) -> float:
        return min(
            max(value, 0.0),
            1.0,
        )
