import asyncio
import os

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.enums import UserRole
from app.repositories.user import UserRepository
from app.schemas.auth import normalize_email


async def bootstrap_admin() -> None:
    email_value = os.getenv(
        "INITIAL_ADMIN_EMAIL",
        "",
    ).strip()

    full_name = os.getenv(
        "INITIAL_ADMIN_FULL_NAME",
        "Platform Administrator",
    ).strip()

    password = os.getenv(
        "INITIAL_ADMIN_PASSWORD",
        "",
    )

    if not email_value:
        raise SystemExit("INITIAL_ADMIN_EMAIL is required.")

    if not full_name:
        raise SystemExit("INITIAL_ADMIN_FULL_NAME is required.")

    if len(password) < 8:
        raise SystemExit("INITIAL_ADMIN_PASSWORD must contain at least 8 characters.")

    email = normalize_email(
        email_value,
    )

    async with AsyncSessionFactory() as session:
        repository = UserRepository(
            session,
        )

        existing_user = await repository.get_by_email(
            email,
        )

        if existing_user is not None:
            print("Initial administrator already exists:")
            print(f"  Email: {existing_user.email}")
            return

        user = await repository.create(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(
                password,
            ),
            role=UserRole.ADMIN,
        )

        print("Initial administrator created:")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")


if __name__ == "__main__":
    asyncio.run(bootstrap_admin())
