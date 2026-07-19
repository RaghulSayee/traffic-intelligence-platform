import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2

from app.core.exceptions import InvalidVideoError


@dataclass(frozen=True)
class VideoMetadata:
    """Technical metadata extracted from a video."""

    duration_seconds: float | None
    frames_per_second: float | None
    frame_count: int | None
    width: int
    height: int
    codec: str | None


class VideoMetadataExtractor(Protocol):
    """Interface for video metadata extractors."""

    def extract(
        self,
        path: Path,
    ) -> VideoMetadata:
        """Extract technical information from a video file."""

        ...


class OpenCVVideoMetadataExtractor:
    """Extract video metadata using OpenCV."""

    def extract(
        self,
        path: Path,
    ) -> VideoMetadata:
        capture = cv2.VideoCapture(str(path))

        try:
            if not capture.isOpened():
                raise InvalidVideoError(
                    "The uploaded file could not be opened as a video."
                )

            successful_read, _ = capture.read()

            if not successful_read:
                raise InvalidVideoError(
                    "The uploaded file does not contain readable video frames."
                )

            width = self._positive_integer(capture.get(cv2.CAP_PROP_FRAME_WIDTH))

            height = self._positive_integer(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

            frames_per_second = self._positive_float(capture.get(cv2.CAP_PROP_FPS))

            frame_count = self._positive_integer(capture.get(cv2.CAP_PROP_FRAME_COUNT))

            if width is None or height is None:
                raise InvalidVideoError("The video resolution could not be determined.")

            duration_seconds: float | None = None

            if frame_count is not None and frames_per_second is not None:
                duration_seconds = frame_count / frames_per_second

            codec = self._decode_fourcc(int(capture.get(cv2.CAP_PROP_FOURCC)))

            return VideoMetadata(
                duration_seconds=duration_seconds,
                frames_per_second=frames_per_second,
                frame_count=frame_count,
                width=width,
                height=height,
                codec=codec,
            )

        finally:
            capture.release()

    @staticmethod
    def _positive_float(
        value: float,
    ) -> float | None:
        if not math.isfinite(value) or value <= 0:
            return None

        return float(value)

    @classmethod
    def _positive_integer(
        cls,
        value: float,
    ) -> int | None:
        positive_value = cls._positive_float(value)

        if positive_value is None:
            return None

        return int(positive_value)

    @staticmethod
    def _decode_fourcc(
        value: int,
    ) -> str | None:
        if value <= 0:
            return None

        characters = [chr((value >> (8 * index)) & 0xFF) for index in range(4)]

        codec = "".join(characters).strip("\x00 ")

        return codec or None
