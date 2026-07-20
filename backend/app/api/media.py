from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from fastapi import (
    HTTPException,
    Request,
    status,
)
from fastapi.responses import StreamingResponse

from app.storage.artifacts import ResolvedArtifact


STREAM_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class ByteRange:
    """One inclusive HTTP byte range."""

    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start + 1


def parse_byte_range(
    range_header: str,
    *,
    file_size: int,
) -> ByteRange:
    """Parse one HTTP Range header."""

    if file_size <= 0:
        raise ValueError("Cannot range-read an empty file.")

    unit, separator, value = range_header.partition("=")

    if separator != "=" or unit.strip().lower() != "bytes" or "," in value:
        raise ValueError("Only one byte range is supported.")

    start_text, separator, end_text = value.strip().partition("-")

    if separator != "-":
        raise ValueError("Invalid byte range.")

    if start_text:
        start = int(start_text)

        end = int(end_text) if end_text else file_size - 1

    else:
        if not end_text:
            raise ValueError("Invalid suffix byte range.")

        suffix_length = int(end_text)

        if suffix_length <= 0:
            raise ValueError("Suffix length must be positive.")

        start = max(
            file_size - suffix_length,
            0,
        )

        end = file_size - 1

    if start < 0 or start >= file_size or end < start:
        raise ValueError("Requested range is unsatisfiable.")

    end = min(
        end,
        file_size - 1,
    )

    return ByteRange(
        start=start,
        end=end,
    )


def create_artifact_response(
    *,
    request: Request,
    artifact: ResolvedArtifact,
) -> StreamingResponse:
    """Stream an artifact with optional range support."""

    range_header = request.headers.get("range")

    status_code = status.HTTP_200_OK

    if range_header:
        try:
            byte_range = parse_byte_range(
                range_header,
                file_size=artifact.size_bytes,
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise HTTPException(
                status_code=(status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE),
                detail="Requested byte range is invalid.",
                headers={"Content-Range": (f"bytes */{artifact.size_bytes}")},
            ) from exc

        status_code = status.HTTP_206_PARTIAL_CONTENT

    else:
        byte_range = ByteRange(
            start=0,
            end=max(
                artifact.size_bytes - 1,
                0,
            ),
        )

    safe_filename = artifact.filename.replace(
        '"',
        "",
    )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(byte_range.length),
        "Content-Disposition": (f'inline; filename="{safe_filename}"'),
    }

    if status_code == status.HTTP_206_PARTIAL_CONTENT:
        headers["Content-Range"] = (
            f"bytes {byte_range.start}-{byte_range.end}/{artifact.size_bytes}"
        )

    return StreamingResponse(
        _read_file_range(
            path=artifact.path,
            byte_range=byte_range,
        ),
        status_code=status_code,
        media_type=artifact.media_type,
        headers=headers,
    )


def _read_file_range(
    *,
    path: Path,
    byte_range: ByteRange,
) -> Iterator[bytes]:
    """Yield only the requested portion of a file."""

    remaining = byte_range.length

    with path.open("rb") as source:
        source.seek(byte_range.start)

        while remaining > 0:
            chunk = source.read(
                min(
                    STREAM_CHUNK_SIZE,
                    remaining,
                )
            )

            if not chunk:
                break

            remaining -= len(chunk)

            yield chunk
