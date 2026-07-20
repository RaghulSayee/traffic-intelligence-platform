from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
    Request,
    Response,
)

from app.api.dependencies import (
    EvidenceMediaServiceDependency,
    ViolationEventServiceDependency,
)
from app.core.exceptions import (
    EvidenceMediaNotFoundError,
    InvalidEvidenceKeyError,
    ViolationEventNotFoundError,
)
from app.models.enums import (
    ReviewStatus,
    ViolationType,
)
from app.schemas.violation_event import (
    ViolationEventListResponse,
    ViolationEventRead,
    ViolationReviewUpdate,
)
from app.api.media import (
    create_artifact_response,
)


router = APIRouter(
    tags=["Violations"],
)


@router.get(
    "",
    response_model=ViolationEventListResponse,
)
async def list_violations(
    service: ViolationEventServiceDependency,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 20,
    violation_type: Annotated[
        ViolationType | None,
        Query(),
    ] = None,
    review_status: Annotated[
        ReviewStatus | None,
        Query(),
    ] = None,
    video_id: Annotated[
        UUID | None,
        Query(),
    ] = None,
    processing_job_id: Annotated[
        UUID | None,
        Query(),
    ] = None,
    camera_id: Annotated[
        UUID | None,
        Query(),
    ] = None,
) -> ViolationEventListResponse:
    """Return detected violations using filters."""

    violations, total = await service.list_violations(
        offset=offset,
        limit=limit,
        violation_type=violation_type,
        review_status=review_status,
        video_id=video_id,
        processing_job_id=(processing_job_id),
        camera_id=camera_id,
    )

    return ViolationEventListResponse(
        items=[
            ViolationEventRead.model_validate(violation) for violation in violations
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{violation_id}",
    response_model=ViolationEventRead,
)
async def get_violation(
    violation_id: UUID,
    service: ViolationEventServiceDependency,
) -> ViolationEventRead:
    """Return one detected violation."""

    try:
        violation = await service.get_violation(violation_id)

    except ViolationEventNotFoundError as exc:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=str(exc),
        ) from exc

    return ViolationEventRead.model_validate(violation)


@router.get(
    "/{violation_id}/evidence/image",
    response_class=Response,
)
async def get_violation_evidence_image(
    violation_id: UUID,
    request: Request,
    service: EvidenceMediaServiceDependency,
) -> Response:
    """Stream a violation evidence image."""

    try:
        artifact = await service.get_violation_image(violation_id)

    except ViolationEventNotFoundError as exc:
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


@router.get(
    "/{violation_id}/evidence/clip",
    response_class=Response,
)
async def get_violation_evidence_clip(
    violation_id: UUID,
    request: Request,
    service: EvidenceMediaServiceDependency,
) -> Response:
    """Stream a violation evidence clip."""

    try:
        artifact = await service.get_violation_clip(violation_id)

    except ViolationEventNotFoundError as exc:
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


@router.patch(
    "/{violation_id}/review",
    response_model=ViolationEventRead,
)
async def review_violation(
    violation_id: UUID,
    payload: ViolationReviewUpdate,
    service: ViolationEventServiceDependency,
) -> ViolationEventRead:
    """Confirm or reject a detected violation."""

    try:
        violation = await service.review_violation(
            violation_id,
            payload,
        )

    except ViolationEventNotFoundError as exc:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=str(exc),
        ) from exc

    return ViolationEventRead.model_validate(violation)
