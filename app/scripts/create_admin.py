import asyncio

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.schemas.auth import CreateAdminRequest
from app.services.auth_service import create_admin_user


async def main() -> None:
    async with AsyncSessionLocal() as db:
        user = await create_admin_user(
            db,
            CreateAdminRequest(
                username=settings.admin_username,
                password=settings.admin_password,
                email=settings.admin_email or None,
            ),
        )
        print(f"Admin user ready: username={user.username} role={user.role}")


if __name__ == "__main__":
    asyncio.run(main())
