from uuid import UUID


class CameraNotFoundError(Exception):
    """Raised when a requested camera does not exist."""

    def __init__(self, camera_id: UUID) -> None:
        self.camera_id = camera_id

        super().__init__(
            f"Camera '{camera_id}' was not found."
        )


class CameraNameConflictError(Exception):
    """Raised when another camera already uses the name."""

    def __init__(self, name: str) -> None:
        self.name = name

        super().__init__(
            f"A camera named '{name}' already exists."
        )