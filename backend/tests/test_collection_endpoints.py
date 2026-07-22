from uuid import uuid4

import pytest

from app.main import app
from app.models.enums import (
    ProcessingJobStatus,
    VideoStatus,
)
from app.services.processing_job import (
    ProcessingJobService,
)
from app.services.video import VideoQueryService


class FakeVideoRepository:
    def __init__(self) -> None:
        self.arguments = None
        self.videos = [object(), object()]

    async def list_videos(
        self,
        **arguments,
    ):
        self.arguments = arguments
        return self.videos, 12


class FakeJobRepository:
    def __init__(self) -> None:
        self.arguments = None
        self.jobs = [object()]

    async def list_jobs(
        self,
        **arguments,
    ):
        self.arguments = arguments
        return self.jobs, 7


@pytest.mark.asyncio
async def test_video_query_service_delegates() -> None:
    repository = FakeVideoRepository()

    service = object.__new__(VideoQueryService)

    service.repository = repository

    camera_id = uuid4()

    videos, total = await service.list_videos(
        offset=10,
        limit=25,
        status=VideoStatus.COMPLETED,
        camera_id=camera_id,
    )

    assert videos == repository.videos
    assert total == 12

    assert repository.arguments == {
        "offset": 10,
        "limit": 25,
        "status": VideoStatus.COMPLETED,
        "camera_id": camera_id,
    }


@pytest.mark.asyncio
async def test_job_query_service_delegates() -> None:
    repository = FakeJobRepository()

    service = object.__new__(ProcessingJobService)

    service.repository = repository

    video_id = uuid4()

    jobs, total = await service.list_jobs(
        offset=5,
        limit=10,
        status=(ProcessingJobStatus.RUNNING),
        video_id=video_id,
    )

    assert jobs == repository.jobs
    assert total == 7

    assert repository.arguments == {
        "offset": 5,
        "limit": 10,
        "status": (ProcessingJobStatus.RUNNING),
        "video_id": video_id,
    }


def test_collection_routes_are_registered() -> None:
    schema = app.openapi()

    video_operation = schema["paths"]["/api/v1/videos"]["get"]

    job_operation = schema["paths"]["/api/v1/jobs"]["get"]

    video_parameters = {
        parameter["name"] for parameter in video_operation["parameters"]
    }

    job_parameters = {parameter["name"] for parameter in job_operation["parameters"]}

    assert video_parameters == {
        "offset",
        "limit",
        "status",
        "camera_id",
    }

    assert job_parameters == {
        "offset",
        "limit",
        "status",
        "video_id",
    }
