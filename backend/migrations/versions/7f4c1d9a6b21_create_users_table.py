"""create users table

Revision ID: 7f4c1d9a6b21
Revises: 2a42cc2b599f
Create Date: 2026-07-22

"""

from typing import (
    Sequence,
    Union,
)

from alembic import op
import sqlalchemy as sa


revision: str = "7f4c1d9a6b21"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "2a42cc2b599f"
branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None
depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    """Create the users table."""

    op.create_table(
        "users",
        sa.Column(
            "email",
            sa.String(length=320),
            nullable=False,
        ),
        sa.Column(
            "full_name",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "hashed_password",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "reviewer",
                name="user_role",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(
                timezone=True,
            ),
            server_default=sa.text(
                "now()",
            ),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(
                timezone=True,
            ),
            server_default=sa.text(
                "now()",
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_users"),
        ),
    )

    op.create_index(
        op.f("ix_users_email"),
        "users",
        ["email"],
        unique=True,
    )

    op.create_index(
        op.f("ix_users_is_active"),
        "users",
        ["is_active"],
        unique=False,
    )

    op.create_index(
        op.f("ix_users_role"),
        "users",
        ["role"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the users table."""

    op.drop_index(
        op.f("ix_users_role"),
        table_name="users",
    )

    op.drop_index(
        op.f("ix_users_is_active"),
        table_name="users",
    )

    op.drop_index(
        op.f("ix_users_email"),
        table_name="users",
    )

    op.drop_table("users")
