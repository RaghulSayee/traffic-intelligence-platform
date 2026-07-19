from dataclasses import dataclass

from app.detection.types import BoundingBox


@dataclass(frozen=True, slots=True)
class TrackedObject:
    """One currently visible object with a persistent identity."""

    track_id: int

    class_id: int
    class_name: str
    confidence: float

    bounding_box: BoundingBox

    age: int
    hits: int
    missed_frames: int
    confirmed: bool

    velocity_x: float
    velocity_y: float


@dataclass(frozen=True, slots=True)
class TrackingResult:
    """Tracking state produced after processing one frame."""

    tracks: tuple[TrackedObject, ...]

    active_track_count: int

    removed_track_ids: tuple[int, ...] = ()

    @property
    def confirmed_tracks(
        self,
    ) -> tuple[TrackedObject, ...]:
        """Return visible tracks that passed confirmation."""

        return tuple(track for track in self.tracks if track.confirmed)

    def count_by_class(self) -> dict[str, int]:
        """Count visible confirmed tracks by class."""

        counts: dict[str, int] = {}

        for track in self.confirmed_tracks:
            counts[track.class_name] = counts.get(track.class_name, 0) + 1

        return counts
