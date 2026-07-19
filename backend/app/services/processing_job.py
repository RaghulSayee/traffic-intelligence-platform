from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ProcessingJobNotFoundError
from app.models.processing_job import ProcessingJob
from app.repositories.processing_job import (
    ProcessingJobRepository,
)


class ProcessingJobService:
    """Provide processing-job query operations."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.repository = ProcessingJobRepository(session)

    async def get_job(
        self,
        job_id: UUID,
    ) -> ProcessingJob:
        job = await self.repository.get_by_id(job_id)

        if job is None:
            raise ProcessingJobNotFoundError(job_id)

        return job
