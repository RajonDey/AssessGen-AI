"""Seed development data: internal org + admin user."""

import asyncio
import os
import uuid

from argon2 import PasswordHasher
from sqlalchemy import select

from app.infrastructure.db.models import Organization, User
from app.infrastructure.db.session import async_session_factory

ph = PasswordHasher()


async def seed() -> None:
    admin_email = os.environ.get("SEED_ADMIN_EMAIL", "admin@assessgen.local")
    admin_password = os.environ.get("SEED_ADMIN_PASSWORD", "admin")

    async with async_session_factory() as session:
        existing = await session.scalar(select(Organization).where(Organization.slug == "internal"))
        if existing is not None:
            print("Seed skipped: organization 'internal' already exists")
            return

        org = Organization(
            id=uuid.uuid4(),
            slug="internal",
            name="Internal",
        )
        session.add(org)
        await session.flush()

        admin = User(
            id=uuid.uuid4(),
            organization_id=org.id,
            email=admin_email,
            password_hash=ph.hash(admin_password),
            role="admin",
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print(f"Seeded organization 'internal' and admin user {admin_email}")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
