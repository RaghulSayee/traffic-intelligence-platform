from collections.abc import (
    Callable,
)
from dataclasses import (
    dataclass,
)
from secrets import (
    compare_digest,
)
from typing import (
    Annotated,
    TypeAlias,
)
from uuid import UUID

from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.api.dependencies import (
    DatabaseSession,
)
from app.core.config import (
    Settings,
    get_settings,
)
from app.core.security import (
    TokenDecodeError,
    decode_access_token,
)
from app.models.enums import (
    UserRole,
)
from app.models.user import User
from app.repositories.user import (
    UserRepository,
)


bearer_scheme = HTTPBearer(
    auto_error=False,
)

SAFE_HTTP_METHODS = {
    "GET",
    "HEAD",
    "OPTIONS",
}


@dataclass(
    frozen=True,
    slots=True,
)
class ServicePrincipal:
    """Represent the trusted Next.js server."""

    name: str = "frontend-server"


AuthenticatedPrincipal: TypeAlias = User | ServicePrincipal


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=(status.HTTP_401_UNAUTHORIZED),
        detail=("Authentication is required."),
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


async def authenticate_user_token(
    *,
    token: str,
    session: DatabaseSession,
) -> User:
    """Validate a JWT and load its active user."""

    try:
        payload = decode_access_token(
            token,
        )

        user_id = UUID(
            payload["sub"],
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        TokenDecodeError,
    ) as exc:
        raise authentication_error() from exc

    repository = UserRepository(
        session,
    )

    user = await repository.get_by_id(
        user_id,
    )

    if user is None or not user.is_active:
        raise authentication_error()

    return user


def get_request_token(
    *,
    request: Request,
    credentials: (HTTPAuthorizationCredentials | None),
    settings: Settings,
) -> str | None:
    """Read a JWT from Bearer auth or the secure cookie."""

    if credentials is not None:
        return credentials.credentials

    return request.cookies.get(
        settings.auth_cookie_name,
    )


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: DatabaseSession,
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> User:
    """Return the active authenticated user."""

    token = get_request_token(
        request=request,
        credentials=credentials,
        settings=settings,
    )

    if not token:
        raise authentication_error()

    user = await authenticate_user_token(
        token=token,
        session=session,
    )

    request.state.authenticated_user = user

    return user


CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]


async def get_authenticated_principal(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: DatabaseSession,
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> AuthenticatedPrincipal:
    """Authenticate a user or the trusted frontend server."""

    supplied_internal_key = request.headers.get(
        "X-Internal-API-Key",
    )

    configured_internal_key = settings.backend_internal_api_key

    if (
        supplied_internal_key
        and configured_internal_key
        and compare_digest(
            supplied_internal_key,
            configured_internal_key,
        )
    ):
        principal = ServicePrincipal()

        request.state.authenticated_user = principal

        return principal

    token = get_request_token(
        request=request,
        credentials=credentials,
        settings=settings,
    )

    if not token:
        raise authentication_error()

    user = await authenticate_user_token(
        token=token,
        session=session,
    )

    request.state.authenticated_user = user

    return user


AuthenticatedRequest = Annotated[
    AuthenticatedPrincipal,
    Depends(
        get_authenticated_principal,
    ),
]


async def require_traffic_access(
    request: Request,
    principal: AuthenticatedRequest,
) -> None:
    """Apply traffic-platform role permissions."""

    method = request.method.upper()

    if method in SAFE_HTTP_METHODS:
        return

    if isinstance(
        principal,
        ServicePrincipal,
    ):
        raise HTTPException(
            status_code=(status.HTTP_403_FORBIDDEN),
            detail=("The internal service may only perform read operations."),
        )

    path = request.url.path

    is_violation_review = "/violations/" in path and path.endswith("/review")

    if is_violation_review:
        allowed_roles = {
            UserRole.ADMIN,
            UserRole.REVIEWER,
        }
    else:
        allowed_roles = {
            UserRole.ADMIN,
        }

    if principal.role not in allowed_roles:
        raise HTTPException(
            status_code=(status.HTTP_403_FORBIDDEN),
            detail=("You do not have permission to perform this action."),
        )


def require_roles(
    *allowed_roles: UserRole,
) -> Callable[..., User]:
    """Create a dependency requiring specific roles."""

    async def role_dependency(
        current_user: CurrentUser,
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=(status.HTTP_403_FORBIDDEN),
                detail=("You do not have permission to perform this action."),
            )

        return current_user

    return role_dependency
