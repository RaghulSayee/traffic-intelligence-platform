from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


ARTIFACT_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
    ".webm": "video/webm",
}


@dataclass(frozen=True, slots=True)
class ResolvedArtifact:
    """A verified artifact stored on the local filesystem."""

    key: str
    path: Path
    filename: str
    media_type: str
    size_bytes: int


class ArtifactStorage(Protocol):
    """Interface for retrieving generated artifacts."""

    def resolve(
        self,
        key: str,
        *,
        allowed_extensions: frozenset[str],
    ) -> ResolvedArtifact:
        """Safely resolve one artifact key."""

        ...


class LocalArtifactStorage:
    """Retrieve artifacts from a protected local directory."""

    def __init__(
        self,
        *,
        root: Path,
    ) -> None:
        self.root = root.resolve()

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def resolve(
        self,
        key: str,
        *,
        allowed_extensions: frozenset[str],
    ) -> ResolvedArtifact:
        """Resolve an artifact while preventing path traversal."""

        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError("Artifact key cannot be blank.")

        key_path = Path(normalized_key)

        if key_path.is_absolute():
            raise ValueError("Absolute artifact paths are not allowed.")

        candidate = (self.root / key_path).resolve()

        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Artifact key escapes the storage directory.") from exc

        if candidate == self.root:
            raise ValueError("Artifact key must identify a file.")

        suffix = candidate.suffix.lower()

        if suffix not in allowed_extensions:
            raise ValueError(f"Unsupported artifact extension: '{suffix}'.")

        if not candidate.is_file():
            raise FileNotFoundError(candidate)

        media_type = ARTIFACT_MEDIA_TYPES.get(
            suffix,
            "application/octet-stream",
        )

        return ResolvedArtifact(
            key=normalized_key,
            path=candidate,
            filename=candidate.name,
            media_type=media_type,
            size_bytes=candidate.stat().st_size,
        )
