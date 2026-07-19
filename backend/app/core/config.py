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
