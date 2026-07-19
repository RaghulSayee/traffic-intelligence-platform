from app.pipelines.base import VideoAnalysisPipeline
from app.pipelines.baseline import BaselineTrafficPipeline


SUPPORTED_PIPELINE_NAMES = {
    "traffic-violation-pipeline",
    "baseline-traffic-pipeline",
}


def create_video_pipeline(
    pipeline_name: str,
) -> VideoAnalysisPipeline:
    """Create a pipeline using its registered name."""

    if pipeline_name in SUPPORTED_PIPELINE_NAMES:
        return BaselineTrafficPipeline()

    raise ValueError(f"Unsupported pipeline: '{pipeline_name}'.")
