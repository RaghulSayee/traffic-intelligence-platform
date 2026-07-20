from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from app.detection.types import Detection
    from app.reasoning.helmet_rider import (
        HelmetRiderAssociation,
    )
    from app.reasoning.no_helmet import (
        NoHelmetTransition,
        NoHelmetViolationSnapshot,
    )
    from app.reasoning.temporal_rider import (
        TemporalRiderAssociation,
    )
    from app.reasoning.triple_riding import (
        TripleRidingTransition,
        TripleRidingViolationSnapshot,
    )
    from app.tracking.types import TrackedObject


VideoFrame = NDArray[np.uint8]


@dataclass(frozen=True)
class VideoContext:
    """Information available when video processing begins."""

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
    """Analysis produced for one decoded video frame."""

    metrics: dict[str, Any] = field(
        default_factory=dict,
    )

    detections: tuple[Detection, ...] = ()

    helmet_detections: tuple[
        Detection,
        ...,
    ] = ()

    tracks: tuple[TrackedObject, ...] = ()

    rider_associations: tuple[
        TemporalRiderAssociation,
        ...,
    ] = ()

    helmet_rider_associations: tuple[
        HelmetRiderAssociation,
        ...,
    ] = ()

    triple_riding_states: tuple[
        TripleRidingViolationSnapshot,
        ...,
    ] = ()

    triple_riding_transitions: tuple[
        TripleRidingTransition,
        ...,
    ] = ()

    no_helmet_states: tuple[
        NoHelmetViolationSnapshot,
        ...,
    ] = ()

    no_helmet_transitions: tuple[
        NoHelmetTransition,
        ...,
    ] = ()

    annotated_frame: VideoFrame | None = None

    analyzed: bool = True


@dataclass(frozen=True)
class PipelineSummary:
    """Final aggregated information produced by a pipeline."""

    metrics: dict[str, Any] = field(
        default_factory=dict,
    )


class VideoAnalysisPipeline(Protocol):
    """Interface implemented by video-analysis pipelines."""

    name: str
    version: str

    def start(
        self,
        context: VideoContext,
    ) -> None:
        """Initialize processing state for a new video."""

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
