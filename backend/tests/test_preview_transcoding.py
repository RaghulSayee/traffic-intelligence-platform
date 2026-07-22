from pathlib import Path
from subprocess import CompletedProcess
from uuid import uuid4

from app.artifacts.traffic_video import (
    TrafficVideoArtifactWriter,
)


def create_writer(
    root: Path,
) -> TrafficVideoArtifactWriter:
    return TrafficVideoArtifactWriter(
        root=root,
        job_id=uuid4(),
        preview_fps=10.0,
        evidence_min_confidence=0.65,
        evidence_cooldown_frames=30,
        max_evidence_frames=0,
        preview_enabled=True,
    )


def test_successful_transcoding_creates_final_preview(
    tmp_path,
    monkeypatch,
) -> None:
    writer = create_writer(tmp_path)

    writer.raw_preview_path.write_bytes(b"opencv-preview")

    monkeypatch.setattr(
        "app.artifacts.traffic_video.shutil.which",
        lambda executable: "/mock/ffmpeg" if executable == "ffmpeg" else None,
    )

    def fake_run(
        command,
        **kwargs,
    ):
        del kwargs

        output_path = Path(command[-1])
        output_path.write_bytes(b"h264-preview")

        return CompletedProcess(
            args=command,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "app.artifacts.traffic_video.subprocess.run",
        fake_run,
    )

    writer._transcode_preview()

    assert writer.preview_path.read_bytes() == (b"h264-preview")

    assert not writer.raw_preview_path.exists()

    writer.abort()


def test_missing_ffmpeg_preserves_original_preview(
    tmp_path,
    monkeypatch,
) -> None:
    writer = create_writer(tmp_path)

    original_preview = b"opencv-preview"

    writer.raw_preview_path.write_bytes(original_preview)

    monkeypatch.setattr(
        "app.artifacts.traffic_video.shutil.which",
        lambda executable: None,
    )

    writer._transcode_preview()

    assert writer.preview_path.read_bytes() == (original_preview)

    assert not writer.raw_preview_path.exists()

    writer.abort()


def test_failed_transcoding_preserves_original_preview(
    tmp_path,
    monkeypatch,
) -> None:
    writer = create_writer(tmp_path)

    original_preview = b"opencv-preview"

    writer.raw_preview_path.write_bytes(original_preview)

    monkeypatch.setattr(
        "app.artifacts.traffic_video.shutil.which",
        lambda executable: "/mock/ffmpeg",
    )

    def fake_run(
        command,
        **kwargs,
    ):
        del kwargs

        Path(command[-1]).write_bytes(b"incomplete-preview")

        return CompletedProcess(
            args=command,
            returncode=1,
            stdout="",
            stderr="conversion failed",
        )

    monkeypatch.setattr(
        "app.artifacts.traffic_video.subprocess.run",
        fake_run,
    )

    writer._transcode_preview()

    assert writer.preview_path.read_bytes() == (original_preview)

    assert not writer.raw_preview_path.exists()

    writer.abort()
