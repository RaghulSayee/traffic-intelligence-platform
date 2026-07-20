from uuid import UUID


class CameraNotFoundError(Exception):
    """Raised when a requested camera does not exist."""

    def __init__(self, camera_id: UUID) -> None:
        self.camera_id = camera_id

        super().__init__(f"Camera '{camera_id}' was not found.")


class CameraNameConflictError(Exception):
    """Raised when another camera already uses the name."""

    def __init__(self, name: str) -> None:
        self.name = name

        super().__init__(f"A camera named '{name}' already exists.")


class UnsupportedVideoError(Exception):
    """Raised when the uploaded file type is unsupported."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class VideoTooLargeError(Exception):
    """Raised when an upload exceeds the configured limit."""

    def __init__(
        self,
        *,
        maximum_bytes: int,
    ) -> None:
        self.maximum_bytes = maximum_bytes

        super().__init__("The uploaded video exceeds the maximum allowed size.")


class InvalidVideoError(Exception):
    """Raised when a file cannot be decoded as a video."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DuplicateVideoError(Exception):
    """Raised when the same video was previously uploaded."""

    def __init__(self, checksum: str) -> None:
        self.checksum = checksum

        super().__init__("A video with the same content has already been uploaded.")


class VideoNotFoundError(Exception):
    """Raised when a requested video does not exist."""

    def __init__(self, video_id: UUID) -> None:
        self.video_id = video_id

        super().__init__(f"Video '{video_id}' was not found.")


class ProcessingJobNotFoundError(Exception):
    """Raised when a processing job does not exist."""

    def __init__(self, job_id: UUID) -> None:
        self.job_id = job_id

        super().__init__(f"Processing job '{job_id}' was not found.")


class WorkerLostLeaseError(Exception):
    """Raised when a worker no longer owns a processing job."""

    def __init__(self, job_id: UUID) -> None:
        self.job_id = job_id

        super().__init__(f"The worker no longer owns processing job '{job_id}'.")


class ViolationEventNotFoundError(Exception):
    """Raised when a requested violation event does not exist."""

    def __init__(
        self,
        violation_id: UUID,
    ) -> None:
        self.violation_id = violation_id

        super().__init__(f"Violation event '{violation_id}' was not found.")


class EvidenceMediaNotFoundError(Exception):
    """Raised when requested evidence media is unavailable."""

    def __init__(
        self,
        *,
        media_kind: str,
        owner_id: UUID,
    ) -> None:
        self.media_kind = media_kind
        self.owner_id = owner_id

        super().__init__(
            f"{media_kind.capitalize()} evidence for '{owner_id}' was not found."
        )


class InvalidEvidenceKeyError(Exception):
    """Raised when an evidence key is unsafe or unsupported."""

    def __init__(self, key: str) -> None:
        self.key = key

        super().__init__("The stored evidence key is invalid.")


class InvalidCameraSceneConfigurationError(Exception):
    """Raised when a stored camera scene cannot be validated."""

    def __init__(
        self,
        camera_id: UUID,
    ) -> None:
        self.camera_id = camera_id

        super().__init__(
            f"Camera '{camera_id}' contains an invalid scene configuration."
        )
