import argparse
import asyncio
from getpass import getpass

from app.core.security import (
    hash_password,
)
from app.db.session import (
    AsyncSessionFactory,
)
from app.models.enums import UserRole
from app.repositories.user import (
    UserRepository,
)
from app.schemas.auth import (
    normalize_email,
)


async def create_admin(
    *,
    email: str,
    full_name: str,
    password: str,
) -> None:
    async with AsyncSessionFactory() as session:
        repository = UserRepository(
            session,
        )

        existing = await repository.get_by_email(
            email,
        )

        if existing is not None:
            raise SystemExit("A user with this email already exists.")

        user = await repository.create(
            email=email,
            full_name=full_name,
            hashed_password=(
                hash_password(
                    password,
                )
            ),
            role=UserRole.ADMIN,
        )

        print("Administrator created:")

        print(f"  ID: {user.id}")

        print(f"  Email: {user.email}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("Create the initial platform administrator."),
    )

    parser.add_argument(
        "--email",
        required=True,
    )

    parser.add_argument(
        "--name",
        required=True,
    )

    arguments = parser.parse_args()

    email = normalize_email(
        arguments.email,
    )

    password = getpass("Administrator password: ")

    confirmation = getpass("Confirm password: ")

    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")

    asyncio.run(
        create_admin(
            email=email,
            full_name=(arguments.name.strip()),
            password=password,
        ),
    )


if __name__ == "__main__":
    main()
