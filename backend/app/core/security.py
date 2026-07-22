from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any

import jwt
from jwt.exceptions import (
    InvalidTokenError,
)
from pwdlib import PasswordHash

from app.core.config import (
    get_settings,
)


password_hash = PasswordHash.recommended()


class TokenDecodeError(ValueError):
    """Raised when an access token cannot be trusted."""


def hash_password(
    password: str,
) -> str:
    """Hash a plaintext password."""

    return password_hash.hash(
        password,
    )


def verify_password(
    password: str,
    hashed_password: str,
) -> bool:
    """Check a plaintext password against its stored hash."""

    return password_hash.verify(
        password,
        hashed_password,
    )


def create_access_token(
    *,
    subject: str,
    role: str,
) -> str:
    """Create a signed JWT access token."""

    settings = get_settings()

    issued_at = datetime.now(
        timezone.utc,
    )

    expires_at = issued_at + timedelta(
        minutes=(settings.jwt_access_token_minutes),
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": issued_at,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=(settings.jwt_algorithm),
    )


def decode_access_token(
    token: str,
) -> dict[str, Any]:
    """Decode and validate a signed JWT access token."""

    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[
                settings.jwt_algorithm,
            ],
        )
    except InvalidTokenError as exc:
        raise TokenDecodeError("The access token is invalid or expired.") from exc

    subject = payload.get("sub")

    if (
        not isinstance(
            subject,
            str,
        )
        or not subject
    ):
        raise TokenDecodeError("The access token has no valid subject.")

    return payload
