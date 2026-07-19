from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.api.dependencies import (
    ProcessingJobServiceDependency,
)
from app.core.exceptions import ProcessingJobNotFoundError
from app.schemas.processing_job import ProcessingJobRead


router = APIRouter(tags=["Processing Jobs"])


@router.get(
    "/{job_id}",
    response_model=ProcessingJobRead,
)
async def get_processing_job(
    job_id: UUID,
    service: ProcessingJobServiceDependency,
) -> ProcessingJobRead:
    """Return the current state of a processing job."""

    try:
        job = await service.get_job(job_id)

    except ProcessingJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ProcessingJobRead.model_validate(job)
