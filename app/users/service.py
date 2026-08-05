from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(func.lower(User.email) == email.lower())
    )
    return result.scalar_one_or_none()
