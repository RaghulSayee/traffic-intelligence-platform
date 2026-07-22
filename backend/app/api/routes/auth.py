from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.api.auth_dependencies import (
    CurrentUser,
    require_roles,
)
from app.api.dependencies import (
    DatabaseSession,
)
from app.core.config import (
    get_settings,
)
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user import (
    UserRepository,
)
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)


router = APIRouter(
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    credentials: LoginRequest,
    session: DatabaseSession,
) -> TokenResponse:
    """Authenticate a user and return an access token."""

    repository = UserRepository(
        session,
    )

    user = await repository.get_by_email(
        credentials.email,
    )

    if (
        user is None
        or not user.is_active
        or not verify_password(
            credentials.password,
            user.hashed_password,
        )
    ):
        raise HTTPException(
            status_code=(status.HTTP_401_UNAUTHORIZED),
            detail=("The email or password is incorrect."),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    settings = get_settings()

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in_seconds=(settings.jwt_access_token_minutes * 60),
        user=UserRead.model_validate(
            user,
        ),
    )


@router.get(
    "/me",
    response_model=UserRead,
)
async def read_current_user(
    current_user: CurrentUser,
) -> User:
    """Return the authenticated user's profile."""

    return current_user


@router.post(
    "/users",
    response_model=UserRead,
    status_code=(status.HTTP_201_CREATED),
)
async def create_user(
    payload: UserCreate,
    session: DatabaseSession,
    _administrator: Annotated[
        User,
        Depends(
            require_roles(
                UserRole.ADMIN,
            ),
        ),
    ],
) -> User:
    """Create a reviewer or administrator account."""

    repository = UserRepository(
        session,
    )

    existing_user = await repository.get_by_email(
        payload.email,
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=("A user with this email already exists."),
        )

    return await repository.create(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(
            payload.password,
        ),
        role=payload.role,
    )
