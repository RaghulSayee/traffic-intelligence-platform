from __future__ import annotations

from dataclasses import dataclass
from math import hypot

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.tracking.types import TrackedObject


INVALID_ASSOCIATION_COST = 1_000_000.0


@dataclass(frozen=True, slots=True)
class RiderAssociationFeatures:
    """Individual signals contributing to one association score."""

    horizontal_overlap_score: float
    anchor_distance_score: float
    vertical_position_score: float
    motion_similarity_score: float
    containment_score: float


@dataclass(frozen=True, slots=True)
class RiderMotorcycleAssociation:
    """A person track associated with a motorcycle track."""

    person_track_id: int
    motorcycle_track_id: int

    score: float
    features: RiderAssociationFeatures


@dataclass(frozen=True, slots=True)
class RiderAssociationResult:
    """Relationship inference produced for one frame."""

    associations: tuple[
        RiderMotorcycleAssociation,
        ...,
    ]

    unassigned_person_track_ids: tuple[int, ...]

    def riders_for_motorcycle(
        self,
        motorcycle_track_id: int,
    ) -> tuple[RiderMotorcycleAssociation, ...]:
        """Return all riders assigned to one motorcycle."""

        return tuple(
            association
            for association in self.associations
            if association.motorcycle_track_id == motorcycle_track_id
        )

    def rider_counts_by_motorcycle(
        self,
    ) -> dict[int, int]:
        """Count assigned riders for each motorcycle."""

        counts: dict[int, int] = {}

        for association in self.associations:
            motorcycle_track_id = association.motorcycle_track_id

            counts[motorcycle_track_id] = (
                counts.get(
                    motorcycle_track_id,
                    0,
                )
                + 1
            )

        return counts


@dataclass(frozen=True, slots=True)
class _CandidateAssociation:
    """Internal scored person-to-motorcycle candidate."""

    person_track_id: int
    motorcycle_track_id: int

    score: float
    features: RiderAssociationFeatures


class RiderMotorcycleAssociator:
    """
    Associate visible person tracks with motorcycle tracks.

    Each person can belong to at most one motorcycle. A motorcycle
    may contain multiple riders up to the configured capacity.
    """

    def __init__(
        self,
        *,
        minimum_score: float,
        max_riders_per_motorcycle: int,
        max_anchor_distance_ratio: float,
        minimum_horizontal_overlap: float,
        minimum_motion_speed: float,
    ) -> None:
        if not 0.0 <= minimum_score <= 1.0:
            raise ValueError("Minimum association score must be between 0 and 1.")

        if max_riders_per_motorcycle <= 0:
            raise ValueError("Maximum riders per motorcycle must be positive.")

        if max_anchor_distance_ratio <= 0:
            raise ValueError("Maximum anchor-distance ratio must be positive.")

        if not 0.0 <= minimum_horizontal_overlap <= 1.0:
            raise ValueError("Minimum horizontal overlap must be between 0 and 1.")

        if minimum_motion_speed < 0:
            raise ValueError("Minimum motion speed cannot be negative.")

        self.minimum_score = minimum_score

        self.max_riders_per_motorcycle = max_riders_per_motorcycle

        self.max_anchor_distance_ratio = max_anchor_distance_ratio

        self.minimum_horizontal_overlap = minimum_horizontal_overlap

        self.minimum_motion_speed = minimum_motion_speed

    def associate(
        self,
        tracks: tuple[TrackedObject, ...],
    ) -> RiderAssociationResult:
        """Infer rider-to-motorcycle relationships for one frame."""

        people = [
            track
            for track in tracks
            if (
                track.confirmed
                and track.missed_frames == 0
                and track.class_name == "person"
            )
        ]

        motorcycles = [
            track
            for track in tracks
            if (
                track.confirmed
                and track.missed_frames == 0
                and track.class_name == "motorcycle"
            )
        ]

        if not people:
            return RiderAssociationResult(
                associations=(),
                unassigned_person_track_ids=(),
            )

        if not motorcycles:
            return RiderAssociationResult(
                associations=(),
                unassigned_person_track_ids=tuple(person.track_id for person in people),
            )

        candidates: dict[
            tuple[int, int],
            _CandidateAssociation,
        ] = {}

        for person in people:
            for motorcycle in motorcycles:
                candidate = self._score_candidate(
                    person=person,
                    motorcycle=motorcycle,
                )

                if candidate is not None:
                    candidates[
                        (
                            person.track_id,
                            motorcycle.track_id,
                        )
                    ] = candidate

        associations = self._solve_assignment(
            people=people,
            motorcycles=motorcycles,
            candidates=candidates,
        )

        assigned_person_ids = {
            association.person_track_id for association in associations
        }

        unassigned_person_ids = tuple(
            person.track_id
            for person in people
            if person.track_id not in assigned_person_ids
        )

        return RiderAssociationResult(
            associations=tuple(
                sorted(
                    associations,
                    key=lambda association: (
                        association.motorcycle_track_id,
                        -association.score,
                        association.person_track_id,
                    ),
                )
            ),
            unassigned_person_track_ids=(unassigned_person_ids),
        )

    def _score_candidate(
        self,
        *,
        person: TrackedObject,
        motorcycle: TrackedObject,
    ) -> _CandidateAssociation | None:
        person_box = person.bounding_box
        motorcycle_box = motorcycle.bounding_box

        horizontal_overlap_score = self._horizontal_overlap_score(
            person=person,
            motorcycle=motorcycle,
        )

        anchor_distance_ratio = self._anchor_distance_ratio(
            person=person,
            motorcycle=motorcycle,
        )

        anchor_distance_score = self._clamp01(
            1.0 - anchor_distance_ratio / self.max_anchor_distance_ratio
        )

        vertical_position_score = self._vertical_position_score(
            person=person,
            motorcycle=motorcycle,
        )

        motion_similarity_score = self._motion_similarity_score(
            person=person,
            motorcycle=motorcycle,
        )

        containment_score = self._containment_score(
            person=person,
            motorcycle=motorcycle,
        )

        person_center_x, person_center_y = person_box.center

        motorcycle_center_x, _ = motorcycle_box.center

        maximum_horizontal_distance = motorcycle_box.width * 1.5

        horizontal_center_distance = abs(person_center_x - motorcycle_center_x)

        person_is_far_below_motorcycle = (
            person_center_y > motorcycle_box.y2 + motorcycle_box.height * 0.5
        )

        passes_horizontal_gate = (
            horizontal_overlap_score >= self.minimum_horizontal_overlap
            or horizontal_center_distance <= maximum_horizontal_distance
        )

        if (
            not passes_horizontal_gate
            or anchor_distance_ratio > self.max_anchor_distance_ratio
            or person_is_far_below_motorcycle
        ):
            return None

        score = (
            0.25 * horizontal_overlap_score
            + 0.30 * anchor_distance_score
            + 0.20 * vertical_position_score
            + 0.15 * motion_similarity_score
            + 0.10 * containment_score
        )

        score = self._clamp01(score)

        if score < self.minimum_score:
            return None

        features = RiderAssociationFeatures(
            horizontal_overlap_score=(horizontal_overlap_score),
            anchor_distance_score=(anchor_distance_score),
            vertical_position_score=(vertical_position_score),
            motion_similarity_score=(motion_similarity_score),
            containment_score=(containment_score),
        )

        return _CandidateAssociation(
            person_track_id=person.track_id,
            motorcycle_track_id=(motorcycle.track_id),
            score=score,
            features=features,
        )

    def _solve_assignment(
        self,
        *,
        people: list[TrackedObject],
        motorcycles: list[TrackedObject],
        candidates: dict[
            tuple[int, int],
            _CandidateAssociation,
        ],
    ) -> list[RiderMotorcycleAssociation]:
        """
        Solve capacity-constrained person-to-motorcycle assignment.

        Each motorcycle is expanded into multiple assignment slots.
        """

        motorcycle_slots: list[tuple[TrackedObject, int]] = []

        for motorcycle in motorcycles:
            for slot_index in range(self.max_riders_per_motorcycle):
                motorcycle_slots.append(
                    (
                        motorcycle,
                        slot_index,
                    )
                )

        cost_matrix = np.full(
            (
                len(people),
                len(motorcycle_slots),
            ),
            INVALID_ASSOCIATION_COST,
            dtype=np.float64,
        )

        for person_index, person in enumerate(people):
            for slot_index, (
                motorcycle,
                rider_slot,
            ) in enumerate(motorcycle_slots):
                candidate = candidates.get(
                    (
                        person.track_id,
                        motorcycle.track_id,
                    )
                )

                if candidate is None:
                    continue

                slot_penalty = rider_slot * 0.01

                cost_matrix[
                    person_index,
                    slot_index,
                ] = 1.0 - candidate.score + slot_penalty

        row_indexes, column_indexes = linear_sum_assignment(cost_matrix)

        associations: list[RiderMotorcycleAssociation] = []

        for person_index, slot_index in zip(
            row_indexes,
            column_indexes,
            strict=True,
        ):
            cost = cost_matrix[
                person_index,
                slot_index,
            ]

            if cost >= INVALID_ASSOCIATION_COST:
                continue

            person = people[int(person_index)]

            motorcycle, _ = motorcycle_slots[int(slot_index)]

            candidate = candidates[
                (
                    person.track_id,
                    motorcycle.track_id,
                )
            ]

            associations.append(
                RiderMotorcycleAssociation(
                    person_track_id=(candidate.person_track_id),
                    motorcycle_track_id=(candidate.motorcycle_track_id),
                    score=candidate.score,
                    features=candidate.features,
                )
            )

        return associations

    @staticmethod
    def _horizontal_overlap_score(
        *,
        person: TrackedObject,
        motorcycle: TrackedObject,
    ) -> float:
        person_box = person.bounding_box
        motorcycle_box = motorcycle.bounding_box

        overlap_width = max(
            min(
                person_box.x2,
                motorcycle_box.x2,
            )
            - max(
                person_box.x1,
                motorcycle_box.x1,
            ),
            0.0,
        )

        normalization_width = max(
            min(
                person_box.width,
                motorcycle_box.width,
            ),
            1.0,
        )

        return RiderMotorcycleAssociator._clamp01(overlap_width / normalization_width)

    def _anchor_distance_ratio(
        self,
        *,
        person: TrackedObject,
        motorcycle: TrackedObject,
    ) -> float:
        person_box = person.bounding_box
        motorcycle_box = motorcycle.bounding_box

        person_anchor_x = person_box.x1 + person_box.width / 2.0

        person_anchor_y = person_box.y2

        motorcycle_anchor_x = motorcycle_box.x1 + motorcycle_box.width / 2.0

        motorcycle_anchor_y = motorcycle_box.y1 + motorcycle_box.height * 0.35

        distance = hypot(
            person_anchor_x - motorcycle_anchor_x,
            person_anchor_y - motorcycle_anchor_y,
        )

        motorcycle_diagonal = max(
            hypot(
                motorcycle_box.width,
                motorcycle_box.height,
            ),
            1.0,
        )

        return distance / motorcycle_diagonal

    @staticmethod
    def _vertical_position_score(
        *,
        person: TrackedObject,
        motorcycle: TrackedObject,
    ) -> float:
        person_box = person.bounding_box
        motorcycle_box = motorcycle.bounding_box

        target_contact_y = motorcycle_box.y1 + motorcycle_box.height * 0.35

        contact_distance = abs(person_box.y2 - target_contact_y)

        contact_score = 1.0 - contact_distance / max(
            motorcycle_box.height,
            1.0,
        )

        _, person_center_y = person_box.center
        _, motorcycle_center_y = motorcycle_box.center

        above_motorcycle_score = 1.0 if person_center_y <= motorcycle_center_y else 0.25

        return RiderMotorcycleAssociator._clamp01(
            0.75 * contact_score + 0.25 * above_motorcycle_score
        )

    def _motion_similarity_score(
        self,
        *,
        person: TrackedObject,
        motorcycle: TrackedObject,
    ) -> float:
        person_velocity = np.array(
            [
                person.velocity_x,
                person.velocity_y,
            ],
            dtype=np.float64,
        )

        motorcycle_velocity = np.array(
            [
                motorcycle.velocity_x,
                motorcycle.velocity_y,
            ],
            dtype=np.float64,
        )

        person_speed = float(np.linalg.norm(person_velocity))

        motorcycle_speed = float(np.linalg.norm(motorcycle_velocity))

        if (
            person_speed < self.minimum_motion_speed
            and motorcycle_speed < self.minimum_motion_speed
        ):
            return 0.5

        if (
            person_speed < self.minimum_motion_speed
            or motorcycle_speed < self.minimum_motion_speed
        ):
            return 0.20

        cosine_similarity = float(
            np.dot(
                person_velocity,
                motorcycle_velocity,
            )
            / (person_speed * motorcycle_speed)
        )

        direction_score = self._clamp01((cosine_similarity + 1.0) / 2.0)

        speed_ratio = min(
            person_speed,
            motorcycle_speed,
        ) / max(
            person_speed,
            motorcycle_speed,
        )

        return self._clamp01(0.70 * direction_score + 0.30 * speed_ratio)

    @staticmethod
    def _containment_score(
        *,
        person: TrackedObject,
        motorcycle: TrackedObject,
    ) -> float:
        person_box = person.bounding_box
        motorcycle_box = motorcycle.bounding_box

        person_anchor_x = person_box.x1 + person_box.width / 2.0

        person_anchor_y = person_box.y2

        expanded_x1 = motorcycle_box.x1 - motorcycle_box.width * 0.35

        expanded_x2 = motorcycle_box.x2 + motorcycle_box.width * 0.35

        expanded_y1 = motorcycle_box.y1 - motorcycle_box.height * 0.75

        expanded_y2 = motorcycle_box.y2 + motorcycle_box.height * 0.25

        inside_horizontal = expanded_x1 <= person_anchor_x <= expanded_x2

        inside_vertical = expanded_y1 <= person_anchor_y <= expanded_y2

        if inside_horizontal and inside_vertical:
            return 1.0

        if inside_horizontal:
            return 0.5

        return 0.0

    @staticmethod
    def _clamp01(
        value: float,
    ) -> float:
        return float(
            min(
                max(value, 0.0),
                1.0,
            )
        )
