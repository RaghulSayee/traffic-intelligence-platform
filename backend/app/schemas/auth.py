from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.enums import UserRole


def normalize_email(
    value: str,
) -> str:
    """Normalize and minimally validate an email address."""

    normalized = value.strip().lower()

    if (
        not normalized
        or "@" not in normalized
        or normalized.startswith("@")
        or normalized.endswith("@")
    ):
        raise ValueError("A valid email address is required.")

    return normalized


class LoginRequest(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=320,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    @field_validator("email")
    @classmethod
    def validate_email(
        cls,
        value: str,
    ) -> str:
        return normalize_email(value)


class UserCreate(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=320,
    )

    full_name: str = Field(
        min_length=2,
        max_length=160,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role: UserRole = UserRole.REVIEWER

    @field_validator("email")
    @classmethod
    def validate_email(
        cls,
        value: str,
    ) -> str:
        return normalize_email(value)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(
        cls,
        value: str,
    ) -> str:
        normalized = " ".join(value.strip().split())

        if len(normalized) < 2:
            raise ValueError("Full name is required.")

        return normalized


class UserRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserRead
