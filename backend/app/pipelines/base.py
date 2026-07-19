from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray


VideoFrame = NDArray[np.uint8]


@dataclass(frozen=True)
class VideoContext:
    """Information available when a pipeline begins processing."""

    video_id: str
    width: int
    height: int
    frames_per_second: float | None
    expected_frame_count: int | None


@dataclass(frozen=True)
class FramePacket:
    """One decoded video frame and its temporal information."""

    frame_number: int
    timestamp_seconds: float
    image: VideoFrame


@dataclass(frozen=True)
class FrameAnalysis:
    """Analysis produced for one video frame."""

    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineSummary:
    """Final aggregated information produced by a pipeline."""

    metrics: dict[str, Any] = field(default_factory=dict)


class VideoAnalysisPipeline(Protocol):
    """Interface implemented by video-analysis pipelines."""

    name: str
    version: str

    def start(
        self,
        context: VideoContext,
    ) -> None:
        """Initialize state before the first frame."""

        ...

    def process_frame(
        self,
        packet: FramePacket,
    ) -> FrameAnalysis:
        """Analyze one frame."""

        ...

    def finish(self) -> PipelineSummary:
        """Return final aggregate metrics."""

        ...
