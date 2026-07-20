from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EvidenceMediaNotFoundError,
    InvalidEvidenceKeyError,
    ProcessingJobNotFoundError,
    ViolationEventNotFoundError,
)
from app.repositories.processing_job import (
    ProcessingJobRepository,
)
from app.repositories.violation_event import (
    ViolationEventRepository,
)
from app.storage.artifacts import (
    ArtifactStorage,
    ResolvedArtifact,
)


IMAGE_EXTENSIONS = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }
)

VIDEO_EXTENSIONS = frozenset(
    {
        ".mp4",
        ".mov",
        ".m4v",
        ".webm",
    }
)


class EvidenceMediaService:
    """Resolve evidence files associated with jobs and violations."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        storage: ArtifactStorage,
    ) -> None:
        self.storage = storage

        self.violation_repository = ViolationEventRepository(session)

        self.job_repository = ProcessingJobRepository(session)

    async def get_violation_image(
        self,
        violation_id: UUID,
    ) -> ResolvedArtifact:
        """Return the evidence image for a violation."""

        violation = await self.violation_repository.get_by_id(violation_id)

        if violation is None:
            raise ViolationEventNotFoundError(violation_id)

        return self._resolve(
            key=violation.evidence_image_key,
            media_kind="image",
            owner_id=violation_id,
            allowed_extensions=IMAGE_EXTENSIONS,
        )

    async def get_violation_clip(
        self,
        violation_id: UUID,
    ) -> ResolvedArtifact:
        """Return the evidence clip for a violation."""

        violation = await self.violation_repository.get_by_id(violation_id)

        if violation is None:
            raise ViolationEventNotFoundError(violation_id)

        return self._resolve(
            key=violation.evidence_clip_key,
            media_kind="clip",
            owner_id=violation_id,
            allowed_extensions=VIDEO_EXTENSIONS,
        )

    async def get_job_preview(
        self,
        job_id: UUID,
    ) -> ResolvedArtifact:
        """Return the annotated preview for a processing job."""

        job = await self.job_repository.get_by_id(job_id)

        if job is None:
            raise ProcessingJobNotFoundError(job_id)

        artifacts = (job.job_metrics or {}).get(
            "artifacts",
            {},
        )

        preview_key = (
            artifacts.get("preview_key") if isinstance(artifacts, dict) else None
        )

        return self._resolve(
            key=preview_key,
            media_kind="preview",
            owner_id=job_id,
            allowed_extensions=VIDEO_EXTENSIONS,
        )

    def _resolve(
        self,
        *,
        key: str | None,
        media_kind: str,
        owner_id: UUID,
        allowed_extensions: frozenset[str],
    ) -> ResolvedArtifact:
        if not key:
            raise EvidenceMediaNotFoundError(
                media_kind=media_kind,
                owner_id=owner_id,
            )

        try:
            return self.storage.resolve(
                key,
                allowed_extensions=(allowed_extensions),
            )

        except ValueError as exc:
            raise InvalidEvidenceKeyError(key) from exc

        except FileNotFoundError as exc:
            raise EvidenceMediaNotFoundError(
                media_kind=media_kind,
                owner_id=owner_id,
            ) from exc
