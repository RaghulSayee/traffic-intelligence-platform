import pytest

from app.core.security import (
    TokenDecodeError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import (
    LoginRequest,
    UserCreate,
)


def test_password_hash_can_be_verified() -> None:
    password = "StrongPassword123!"

    hashed = hash_password(
        password,
    )

    assert hashed != password
    assert verify_password(
        password,
        hashed,
    )
    assert not verify_password(
        "WrongPassword123!",
        hashed,
    )


def test_access_token_round_trip() -> None:
    token = create_access_token(
        subject=("00000000-0000-0000-0000-000000000001"),
        role="admin",
    )

    payload = decode_access_token(
        token,
    )

    assert payload["sub"] == "00000000-0000-0000-0000-000000000001"

    assert payload["role"] == "admin"


def test_invalid_token_is_rejected() -> None:
    with pytest.raises(
        TokenDecodeError,
    ):
        decode_access_token(
            "invalid-token",
        )


def test_login_email_is_normalized() -> None:
    request = LoginRequest(
        email="  ADMIN@EXAMPLE.COM ",
        password="StrongPassword123!",
    )

    assert request.email == "admin@example.com"


def test_new_user_defaults_to_reviewer() -> None:
    user = UserCreate(
        email="reviewer@example.com",
        full_name="Traffic Reviewer",
        password="StrongPassword123!",
    )

    assert user.role.value == "reviewer"
