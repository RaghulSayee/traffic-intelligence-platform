from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
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
from app.models.enums import (
    ProcessingJobStatus,
)
from app.schemas.processing_job import (
    ProcessingJobListResponse,
    ProcessingJobRead,
)


router = APIRouter(tags=["Processing Jobs"])


@router.get(
    "",
    response_model=(ProcessingJobListResponse),
)
async def list_processing_jobs(
    service: ProcessingJobServiceDependency,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 20,
    job_status: Annotated[
        ProcessingJobStatus | None,
        Query(alias="status"),
    ] = None,
    video_id: Annotated[
        UUID | None,
        Query(),
    ] = None,
) -> ProcessingJobListResponse:
    """Return processing jobs using filters."""

    jobs, total = await service.list_jobs(
        offset=offset,
        limit=limit,
        status=job_status,
        video_id=video_id,
    )

    return ProcessingJobListResponse(
        items=[ProcessingJobRead.model_validate(job) for job in jobs],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{job_id}",
    response_model=ProcessingJobRead,
)
async def get_processing_job(
    job_id: UUID,
    service: ProcessingJobServiceDependency,
) -> ProcessingJobRead:
    """Return the state of a job."""

    try:
        job = await service.get_job(job_id)

    except ProcessingJobNotFoundError as exc:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
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
    """Stream the annotated job preview."""

    try:
        artifact = await service.get_job_preview(job_id)

    except ProcessingJobNotFoundError as exc:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=str(exc),
        ) from exc

    except EvidenceMediaNotFoundError as exc:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
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
