from uuid import uuid4

import pytest
from fastapi import (
    HTTPException,
)
from fastapi.testclient import (
    TestClient,
)
from starlette.requests import (
    Request,
)

from app.api.auth_dependencies import (
    ServicePrincipal,
    require_traffic_access,
)
from app.main import app
from app.models.enums import (
    UserRole,
)
from app.models.user import User


client = TestClient(app)


def build_request(
    method: str,
    path: str,
) -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "scheme": "http",
            "server": (
                "testserver",
                80,
            ),
            "client": (
                "testclient",
                50000,
            ),
        },
    )


def build_user(
    role: UserRole,
) -> User:
    return User(
        id=uuid4(),
        email=(f"{role.value}@example.com"),
        full_name=(f"{role.value.title()} User"),
        hashed_password="hash",
        role=role,
        is_active=True,
    )


def test_traffic_route_requires_authentication() -> None:
    response = client.get(
        "/api/v1/cameras?limit=1",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reviewer_can_review_violation() -> None:
    request = build_request(
        "PATCH",
        ("/api/v1/violations/00000000-0000-0000-0000-000000000001/review"),
    )

    await require_traffic_access(
        request,
        build_user(
            UserRole.REVIEWER,
        ),
    )


@pytest.mark.asyncio
async def test_reviewer_cannot_delete_video() -> None:
    request = build_request(
        "DELETE",
        ("/api/v1/videos/00000000-0000-0000-0000-000000000001"),
    )

    with pytest.raises(
        HTTPException,
    ) as exception:
        await require_traffic_access(
            request,
            build_user(
                UserRole.REVIEWER,
            ),
        )

    assert exception.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_modify_camera() -> None:
    request = build_request(
        "PATCH",
        ("/api/v1/cameras/00000000-0000-0000-0000-000000000001"),
    )

    await require_traffic_access(
        request,
        build_user(
            UserRole.ADMIN,
        ),
    )


@pytest.mark.asyncio
async def test_internal_service_is_read_only() -> None:
    request = build_request(
        "DELETE",
        ("/api/v1/videos/00000000-0000-0000-0000-000000000001"),
    )

    with pytest.raises(
        HTTPException,
    ) as exception:
        await require_traffic_access(
            request,
            ServicePrincipal(),
        )

    assert exception.value.status_code == 403
