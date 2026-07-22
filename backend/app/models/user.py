from sqlalchemy import (
    Boolean,
    Enum,
    String,
    true,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import UserRole


class User(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    """A user authorized to access the platform."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
        ),
        nullable=False,
        default=UserRole.REVIEWER,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )
