import asyncio
import os
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import UploadFile

from app.core.exceptions import (
    UnsupportedVideoError,
    VideoTooLargeError,
)
from app.storage.base import StoredVideo


SUPPORTED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
}


class LocalVideoStorage:
    """Store uploaded videos on the local filesystem."""

    def __init__(
        self,
        *,
        root: Path,
        maximum_bytes: int,
        chunk_size_bytes: int,
    ) -> None:
        self.root = root.resolve()
        self.maximum_bytes = maximum_bytes
        self.chunk_size_bytes = chunk_size_bytes

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    async def save(
        self,
        upload: UploadFile,
    ) -> StoredVideo:
        """Write a video in chunks while calculating its checksum."""

        original_filename = Path(upload.filename or "").name

        suffix = Path(original_filename).suffix.lower()

        if suffix not in SUPPORTED_VIDEO_EXTENSIONS:
            raise UnsupportedVideoError(
                "Supported video extensions are: "
                f"{', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}."
            )

        storage_key = f"{uuid4()}{suffix}"

        final_path = self.resolve_path(storage_key)
        temporary_path = self.resolve_path(f".{storage_key}.part")

        checksum = sha256()
        total_bytes = 0

        try:
            async with aiofiles.open(
                temporary_path,
                mode="wb",
            ) as destination:
                while True:
                    chunk = await upload.read(self.chunk_size_bytes)

                    if not chunk:
                        break

                    total_bytes += len(chunk)

                    if total_bytes > self.maximum_bytes:
                        raise VideoTooLargeError(maximum_bytes=self.maximum_bytes)

                    checksum.update(chunk)
                    await destination.write(chunk)

            await asyncio.to_thread(
                os.replace,
                temporary_path,
                final_path,
            )

        except Exception:
            await asyncio.to_thread(
                temporary_path.unlink,
                missing_ok=True,
            )
            raise

        finally:
            await upload.close()

        return StoredVideo(
            key=storage_key,
            path=final_path,
            size_bytes=total_bytes,
            checksum_sha256=checksum.hexdigest(),
        )

    async def delete(
        self,
        key: str,
    ) -> None:
        """Delete a stored video if it exists."""

        path = self.resolve_path(key)

        await asyncio.to_thread(
            path.unlink,
            missing_ok=True,
        )

    def resolve_path(
        self,
        key: str,
    ) -> Path:
        """Safely resolve a key inside the storage directory."""

        candidate = (self.root / key).resolve()

        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("Invalid video storage key.")

        return candidate
