"""
PulseOps — Shared User Utility Service
Find-or-create placeholder users for task assignment flows.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import User, UserRole


async def find_or_create_user_by_name(db: AsyncSession, name: str) -> User:
    """Find user by name (case-insensitive) or create a placeholder user."""
    result = await db.execute(
        select(User).where(func.lower(User.name) == name.lower().strip())
    )
    user = result.scalar_one_or_none()
    if user:
        return user
    # Create placeholder
    first = name.strip().split()[0].lower()
    email = f"{first}.{abs(hash(name)) % 10000}@pulseops.internal"
    new_user = User(
        name=name.strip(),
        email=email,
        role=UserRole.contributor,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()  # get ID without committing
    return new_user
