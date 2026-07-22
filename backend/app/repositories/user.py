from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.models.enums import UserRole
from app.models.user import User


class UserRepository:
    """Database access operations for users."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        return await self.session.get(
            User,
            user_id,
        )

    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        result = await self.session.execute(
            select(User).where(
                User.email == email.strip().lower(),
            ),
        )

        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        full_name: str,
        hashed_password: str,
        role: UserRole,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=(email.strip().lower()),
            full_name=full_name,
            hashed_password=(hashed_password),
            role=role,
            is_active=is_active,
        )

        self.session.add(user)

        await self.session.commit()
        await self.session.refresh(user)

        return user
