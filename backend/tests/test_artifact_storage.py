from pathlib import Path

import pytest

from app.storage.artifacts import (
    LocalArtifactStorage,
)


def test_artifact_storage_resolves_safe_file(
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / "job-1" / "preview.mp4"

    artifact_path.parent.mkdir()
    artifact_path.write_bytes(b"video-data")

    storage = LocalArtifactStorage(root=tmp_path)

    result = storage.resolve(
        "job-1/preview.mp4",
        allowed_extensions=frozenset({".mp4"}),
    )

    assert result.path == artifact_path
    assert result.media_type == "video/mp4"
    assert result.size_bytes == 10


def test_artifact_storage_rejects_path_traversal(
    tmp_path: Path,
) -> None:
    storage = LocalArtifactStorage(root=tmp_path)

    with pytest.raises(ValueError):
        storage.resolve(
            "../../.env",
            allowed_extensions=frozenset({".jpg"}),
        )


def test_artifact_storage_rejects_wrong_extension(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "secret.txt"
    file_path.write_text("secret")

    storage = LocalArtifactStorage(root=tmp_path)

    with pytest.raises(ValueError):
        storage.resolve(
            "secret.txt",
            allowed_extensions=frozenset({".jpg"}),
        )
