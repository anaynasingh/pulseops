"""
FastAPI dependency injection: current user, DB session, etc.
"""
import time
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.session import get_db
from app.core.security import decode_token
from app.models.models import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)

# ── User lookup cache ──────────────────────────────────────────────────────────
# Supabase is in Sydney — verifying every request costs ~800ms-1s.
# Cache user objects by user_id for 5 minutes (TTL matches token ~7 days).
_user_cache: dict = {}   # user_id → (timestamp, User)
_USER_CACHE_TTL = 300    # 5 minutes


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # Check cache first
    cached = _user_cache.get(user_id)
    if cached and (time.time() - cached[0]) < _USER_CACHE_TTL:
        return cached[1]

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    _user_cache[user_id] = (time.time(), user)   # cache it
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def require_writer(current_user: User = Depends(get_current_user)) -> User:
    """Blocks viewer-role accounts from any write operation."""
    if current_user.role == UserRole.viewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has view-only access. Contact an admin to request write access.",
        )
    return current_user


async def get_db_for_user(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """DB session with RLS context: stamps the current user's ID and role into
    Postgres session variables so RLS policies can enforce row-level ownership."""
    await db.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": str(current_user.id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_user_role', :role, true)"),
        {"role": current_user.role.value},
    )
    yield db
