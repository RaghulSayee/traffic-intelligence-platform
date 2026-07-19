from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Pixel coordinates representing one detected object."""

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        """Return the bounding-box width."""

        return max(self.x2 - self.x1, 0.0)

    @property
    def height(self) -> float:
        """Return the bounding-box height."""

        return max(self.y2 - self.y1, 0.0)

    @property
    def area(self) -> float:
        """Return the bounding-box area."""

        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        """Return the center point of the bounding box."""

        return (
            (self.x1 + self.x2) / 2.0,
            (self.y1 + self.y2) / 2.0,
        )

    def clipped(
        self,
        *,
        image_width: int,
        image_height: int,
    ) -> "BoundingBox":
        """Return coordinates restricted to the image boundaries."""

        return BoundingBox(
            x1=min(max(self.x1, 0.0), float(image_width)),
            y1=min(max(self.y1, 0.0), float(image_height)),
            x2=min(max(self.x2, 0.0), float(image_width)),
            y2=min(max(self.y2, 0.0), float(image_height)),
        )

    def as_integer_tuple(
        self,
    ) -> tuple[int, int, int, int]:
        """Return coordinates suitable for OpenCV drawing."""

        return (
            round(self.x1),
            round(self.y1),
            round(self.x2),
            round(self.y2),
        )


@dataclass(frozen=True, slots=True)
class Detection:
    """One object detected in a video frame."""

    class_id: int
    class_name: str
    confidence: float
    bounding_box: BoundingBox
    model_name: str


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """All retained detections produced for one frame."""

    detections: tuple[Detection, ...]
    inference_time_ms: float
    image_width: int
    image_height: int

    @property
    def count(self) -> int:
        """Return the number of retained detections."""

        return len(self.detections)

    def count_by_class(self) -> dict[str, int]:
        """Aggregate detections by their class names."""

        counts: dict[str, int] = {}

        for detection in self.detections:
            counts[detection.class_name] = counts.get(detection.class_name, 0) + 1

        return counts
