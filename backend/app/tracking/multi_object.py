from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

from app.detection.types import Detection
from app.tracking.geometry import (
    intersection_over_union,
)
from app.tracking.kalman import (
    BoundingBoxKalmanFilter,
)
from app.tracking.types import (
    TrackedObject,
    TrackingResult,
)


INVALID_ASSOCIATION_COST = 1_000_000.0


@dataclass(slots=True)
class _Track:
    """Mutable internal state for one tracked object."""

    track_id: int

    class_id: int
    class_name: str
    confidence: float

    kalman_filter: BoundingBoxKalmanFilter

    last_timestamp_seconds: float

    age: int = 1
    hits: int = 1
    missed_frames: int = 0
    confirmed: bool = False

    def predict(
        self,
        timestamp_seconds: float,
    ) -> None:
        delta_seconds = max(
            timestamp_seconds - self.last_timestamp_seconds,
            0.001,
        )

        self.kalman_filter.predict(delta_seconds=delta_seconds)

        self.last_timestamp_seconds = timestamp_seconds

        self.age += 1

    def update(
        self,
        detection: Detection,
    ) -> None:
        self.kalman_filter.update(detection.bounding_box)

        self.confidence = detection.confidence

        self.hits += 1
        self.missed_frames = 0

    def mark_missed(self) -> None:
        self.missed_frames += 1

    def to_public(self) -> TrackedObject:
        velocity_x, velocity_y = self.kalman_filter.velocity

        return TrackedObject(
            track_id=self.track_id,
            class_id=self.class_id,
            class_name=self.class_name,
            confidence=self.confidence,
            bounding_box=(self.kalman_filter.bounding_box),
            age=self.age,
            hits=self.hits,
            missed_frames=self.missed_frames,
            confirmed=self.confirmed,
            velocity_x=velocity_x,
            velocity_y=velocity_y,
        )


class MultiObjectTracker:
    """
    Track multiple objects using motion and IoU association.

    The association flow follows a ByteTrack-style strategy:

    1. Match tracks with high-confidence detections.
    2. Match remaining tracks with low-confidence detections.
    3. Create new tracks from unmatched high-confidence detections.
    """

    def __init__(
        self,
        *,
        high_confidence_threshold: float,
        low_confidence_threshold: float,
        primary_iou_threshold: float,
        secondary_iou_threshold: float,
        minimum_confirmed_hits: int,
        maximum_missed_frames: int,
        process_noise: float,
        measurement_noise: float,
    ) -> None:
        if not (0.0 <= low_confidence_threshold <= high_confidence_threshold <= 1.0):
            raise ValueError("Tracker confidence thresholds are invalid.")

        for threshold in (
            primary_iou_threshold,
            secondary_iou_threshold,
        ):
            if not 0.0 <= threshold <= 1.0:
                raise ValueError("IoU thresholds must be between 0 and 1.")

        if minimum_confirmed_hits <= 0:
            raise ValueError("Minimum confirmed hits must be positive.")

        if maximum_missed_frames < 0:
            raise ValueError("Maximum missed frames cannot be negative.")

        self.high_confidence_threshold = high_confidence_threshold

        self.low_confidence_threshold = low_confidence_threshold

        self.primary_iou_threshold = primary_iou_threshold

        self.secondary_iou_threshold = secondary_iou_threshold

        self.minimum_confirmed_hits = minimum_confirmed_hits

        self.maximum_missed_frames = maximum_missed_frames

        self.process_noise = process_noise
        self.measurement_noise = measurement_noise

        self.next_track_id = 1

        self.tracks: dict[int, _Track] = {}

    def update(
        self,
        *,
        detections: tuple[Detection, ...],
        timestamp_seconds: float,
    ) -> TrackingResult:
        """Update all tracks using one frame of detections."""

        current_tracks = list(self.tracks.values())

        for track in current_tracks:
            track.predict(timestamp_seconds)

        high_detections = [
            detection
            for detection in detections
            if detection.confidence >= self.high_confidence_threshold
        ]

        low_detections = [
            detection
            for detection in detections
            if (
                self.low_confidence_threshold
                <= detection.confidence
                < self.high_confidence_threshold
            )
        ]

        (
            primary_matches,
            unmatched_track_indexes,
            unmatched_high_indexes,
        ) = self._associate(
            tracks=current_tracks,
            detections=high_detections,
            minimum_iou=(self.primary_iou_threshold),
        )

        matched_track_ids: set[int] = set()

        for track_index, detection_index in primary_matches:
            track = current_tracks[track_index]

            track.update(high_detections[detection_index])

            self._confirm_if_ready(track)

            matched_track_ids.add(track.track_id)

        remaining_tracks = [current_tracks[index] for index in unmatched_track_indexes]

        (
            secondary_matches,
            unmatched_remaining_indexes,
            _,
        ) = self._associate(
            tracks=remaining_tracks,
            detections=low_detections,
            minimum_iou=(self.secondary_iou_threshold),
        )

        for track_index, detection_index in secondary_matches:
            track = remaining_tracks[track_index]

            track.update(low_detections[detection_index])

            self._confirm_if_ready(track)

            matched_track_ids.add(track.track_id)

        unmatched_after_secondary = {
            remaining_tracks[index].track_id for index in unmatched_remaining_indexes
        }

        for track in current_tracks:
            if (
                track.track_id not in matched_track_ids
                and track.track_id in unmatched_after_secondary
            ):
                track.mark_missed()

        for detection_index in unmatched_high_indexes:
            detection = high_detections[detection_index]

            self._create_track(
                detection=detection,
                timestamp_seconds=(timestamp_seconds),
            )

        removed_track_ids: list[int] = []

        for track_id, track in list(self.tracks.items()):
            if track.missed_frames > self.maximum_missed_frames:
                removed_track_ids.append(track_id)

                del self.tracks[track_id]

        visible_tracks = tuple(
            track.to_public()
            for track in self.tracks.values()
            if track.missed_frames == 0
        )

        return TrackingResult(
            tracks=visible_tracks,
            active_track_count=len(self.tracks),
            removed_track_ids=tuple(removed_track_ids),
        )

    def reset(self) -> None:
        """Remove all state before processing another video."""

        self.next_track_id = 1
        self.tracks.clear()

    def _create_track(
        self,
        *,
        detection: Detection,
        timestamp_seconds: float,
    ) -> None:
        track = _Track(
            track_id=self.next_track_id,
            class_id=detection.class_id,
            class_name=detection.class_name,
            confidence=detection.confidence,
            kalman_filter=(
                BoundingBoxKalmanFilter(
                    bounding_box=(detection.bounding_box),
                    process_noise=(self.process_noise),
                    measurement_noise=(self.measurement_noise),
                )
            ),
            last_timestamp_seconds=(timestamp_seconds),
            confirmed=(self.minimum_confirmed_hits <= 1),
        )

        self.tracks[track.track_id] = track

        self.next_track_id += 1

    def _confirm_if_ready(
        self,
        track: _Track,
    ) -> None:
        if track.hits >= self.minimum_confirmed_hits:
            track.confirmed = True

    @staticmethod
    def _associate(
        *,
        tracks: list[_Track],
        detections: list[Detection],
        minimum_iou: float,
    ) -> tuple[
        list[tuple[int, int]],
        list[int],
        list[int],
    ]:
        if not tracks:
            return (
                [],
                [],
                list(range(len(detections))),
            )

        if not detections:
            return (
                [],
                list(range(len(tracks))),
                [],
            )

        cost_matrix = np.full(
            (
                len(tracks),
                len(detections),
            ),
            INVALID_ASSOCIATION_COST,
            dtype=np.float64,
        )

        for track_index, track in enumerate(tracks):
            track_box = track.kalman_filter.bounding_box

            for detection_index, detection in enumerate(detections):
                if detection.class_id != track.class_id:
                    continue

                iou = intersection_over_union(
                    track_box,
                    detection.bounding_box,
                )

                if iou < minimum_iou:
                    continue

                cost_matrix[
                    track_index,
                    detection_index,
                ] = 1.0 - iou

        row_indexes, column_indexes = linear_sum_assignment(cost_matrix)

        matches: list[tuple[int, int]] = []

        matched_track_indexes: set[int] = set()
        matched_detection_indexes: set[int] = set()

        for track_index, detection_index in zip(
            row_indexes,
            column_indexes,
            strict=True,
        ):
            if (
                cost_matrix[
                    track_index,
                    detection_index,
                ]
                >= INVALID_ASSOCIATION_COST
            ):
                continue

            matches.append(
                (
                    int(track_index),
                    int(detection_index),
                )
            )

            matched_track_indexes.add(int(track_index))

            matched_detection_indexes.add(int(detection_index))

        unmatched_track_indexes = [
            index for index in range(len(tracks)) if index not in matched_track_indexes
        ]

        unmatched_detection_indexes = [
            index
            for index in range(len(detections))
            if index not in matched_detection_indexes
        ]

        return (
            matches,
            unmatched_track_indexes,
            unmatched_detection_indexes,
        )
