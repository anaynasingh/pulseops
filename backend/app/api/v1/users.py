from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import UserOut
from app.core.deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active team members — used for task assignment dropdowns."""
    result = await db.execute(
        select(User)
        .where(
            User.is_active == True,
            or_(User.ms_oid.isnot(None), User.password_hash.isnot(None)),  # anyone who has logged in (SSO or legacy password)
            User.email.like("%prospect33.com%"),  # only real team members
        )
        .order_by(User.name)
    )
    return [UserOut.model_validate(u) for u in result.scalars().all()]
