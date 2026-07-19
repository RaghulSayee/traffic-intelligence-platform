from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from fastapi import UploadFile


@dataclass(frozen=True)
class StoredVideo:
    """Result produced after storing an uploaded video."""

    key: str
    path: Path
    size_bytes: int
    checksum_sha256: str


class VideoStorage(Protocol):
    """Interface implemented by video-storage providers."""

    async def save(
        self,
        upload: UploadFile,
    ) -> StoredVideo:
        """Store an uploaded video and return its storage details."""

        ...

    async def delete(
        self,
        key: str,
    ) -> None:
        """Delete a stored video."""

        ...

    def resolve_path(
        self,
        key: str,
    ) -> Path:
        """Resolve a storage key to its local filesystem path."""

        ...
