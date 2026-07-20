from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Traffic Intelligence API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = (
        "postgresql+asyncpg://traffic_user:"
        "traffic_password@localhost:5432/traffic_intelligence"
    )
    database_echo: bool = False

    video_storage_path: Path = Path("storage/videos")
    max_video_upload_mb: int = 500
    upload_chunk_size_bytes: int = 1024 * 1024

    worker_poll_interval_seconds: float = 2.0
    worker_lease_seconds: int = 120
    worker_progress_interval_frames: int = 10
    worker_max_attempts: int = 3
    worker_recovery_batch_size: int = 20

    detector_model_path: str = "yolo26n.pt"
    detector_device: str = "auto"
    detector_confidence_threshold: float = 0.35
    detector_iou_threshold: float = 0.50
    detector_image_size: int = 640

    helmet_detector_enabled: bool = False
    helmet_detector_model_path: str = "models/helmet_detector.pt"
    helmet_detector_device: str = "auto"
    helmet_detector_confidence_threshold: float = 0.40
    helmet_detector_iou_threshold: float = 0.50
    helmet_detector_image_size: int = 640

    evidence_storage_path: Path = Path("storage/evidence")

    detector_frame_stride: int = 5

    evidence_min_confidence: float = 0.65
    evidence_cooldown_frames: int = 30
    max_evidence_frames: int = 20

    annotated_preview_enabled: bool = True

    tracker_high_confidence_threshold: float = 0.60
    tracker_low_confidence_threshold: float = 0.35

    tracker_primary_iou_threshold: float = 0.30
    tracker_secondary_iou_threshold: float = 0.15

    tracker_min_confirmed_hits: int = 2
    tracker_max_missed_frames: int = 12

    tracker_process_noise: float = 1.0
    tracker_measurement_noise: float = 10.0

    rider_association_minimum_score: float = 0.55
    rider_association_max_riders_per_motorcycle: int = 3

    rider_association_max_anchor_distance_ratio: float = 2.0
    rider_association_minimum_horizontal_overlap: float = 0.05

    rider_association_minimum_motion_speed: float = 5.0

    rider_temporal_confirmation_frames: int = 3
    rider_temporal_max_missed_frames: int = 2
    rider_temporal_score_alpha: float = 0.40

    triple_riding_minimum_riders: int = 3
    triple_riding_confirmation_frames: int = 3
    triple_riding_maximum_missed_frames: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def max_video_upload_bytes(self) -> int:
        """Return the maximum upload size in bytes."""

        return self.max_video_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Create and cache one settings object."""

    return Settings()
