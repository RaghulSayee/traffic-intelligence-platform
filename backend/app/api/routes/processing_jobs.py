from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    Response,
    status,
)

from app.api.dependencies import (
    EvidenceMediaServiceDependency,
    ProcessingJobServiceDependency,
)
from app.api.media import (
    create_artifact_response,
)
from app.core.exceptions import (
    EvidenceMediaNotFoundError,
    InvalidEvidenceKeyError,
    ProcessingJobNotFoundError,
)
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


@router.get(
    "/{job_id}/preview",
    response_class=Response,
)
async def get_processing_job_preview(
    job_id: UUID,
    request: Request,
    service: EvidenceMediaServiceDependency,
) -> Response:
    """Stream the annotated preview for a job."""

    try:
        artifact = await service.get_job_preview(job_id)

    except ProcessingJobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except EvidenceMediaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except InvalidEvidenceKeyError as exc:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
            detail=str(exc),
        ) from exc

    return create_artifact_response(
        request=request,
        artifact=artifact,
    )
