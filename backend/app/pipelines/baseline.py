import cv2
import numpy as np

from app.pipelines.base import (
    FrameAnalysis,
    FramePacket,
    PipelineSummary,
    VideoContext,
)


class BaselineTrafficPipeline:
    """
    Analyze video quality and temporal motion.

    This is not yet an object-detection model. It validates the worker
    architecture and demonstrates stateful frame-to-frame processing.
    """

    name = "baseline-traffic-pipeline"
    version = "0.1.0"

    def __init__(
        self,
        *,
        motion_threshold: int = 25,
        active_motion_ratio: float = 0.02,
    ) -> None:
        self.motion_threshold = motion_threshold
        self.active_motion_ratio = active_motion_ratio

        self.previous_gray: np.ndarray | None = None

        self.processed_frames = 0
        self.frames_with_motion = 0

        self.total_brightness = 0.0
        self.total_sharpness = 0.0
        self.total_motion_ratio = 0.0

    def start(
        self,
        context: VideoContext,
    ) -> None:
        """Reset pipeline state for a new video."""

        self.previous_gray = None

        self.processed_frames = 0
        self.frames_with_motion = 0

        self.total_brightness = 0.0
        self.total_sharpness = 0.0
        self.total_motion_ratio = 0.0

    def process_frame(
        self,
        packet: FramePacket,
    ) -> FrameAnalysis:
        """Calculate image-quality and temporal-motion metrics."""

        gray = cv2.cvtColor(
            packet.image,
            cv2.COLOR_BGR2GRAY,
        )

        brightness = float(np.mean(gray) / 255.0)

        sharpness = float(
            cv2.Laplacian(
                gray,
                cv2.CV_64F,
            ).var()
        )

        motion_ratio = self._calculate_motion_ratio(gray)

        self.processed_frames += 1

        self.total_brightness += brightness
        self.total_sharpness += sharpness
        self.total_motion_ratio += motion_ratio

        if motion_ratio >= self.active_motion_ratio:
            self.frames_with_motion += 1

        self.previous_gray = gray

        return FrameAnalysis(
            metrics={
                "brightness": brightness,
                "sharpness": sharpness,
                "motion_ratio": motion_ratio,
            }
        )

    def finish(self) -> PipelineSummary:
        """Return video-level aggregate metrics."""

        if self.processed_frames == 0:
            return PipelineSummary(
                metrics={
                    "processed_frames": 0,
                }
            )

        processed = float(self.processed_frames)

        return PipelineSummary(
            metrics={
                "processed_frames": self.processed_frames,
                "average_brightness": (self.total_brightness / processed),
                "average_sharpness": (self.total_sharpness / processed),
                "average_motion_ratio": (self.total_motion_ratio / processed),
                "motion_frame_percentage": (
                    self.frames_with_motion / processed * 100.0
                ),
            }
        )

    def _calculate_motion_ratio(
        self,
        current_gray: np.ndarray,
    ) -> float:
        """Estimate changed pixels between consecutive frames."""

        if self.previous_gray is None:
            return 0.0

        difference = cv2.absdiff(
            self.previous_gray,
            current_gray,
        )

        _, motion_mask = cv2.threshold(
            difference,
            self.motion_threshold,
            255,
            cv2.THRESH_BINARY,
        )

        changed_pixels = int(cv2.countNonZero(motion_mask))

        total_pixels = int(motion_mask.size)

        if total_pixels == 0:
            return 0.0

        return float(changed_pixels / total_pixels)
