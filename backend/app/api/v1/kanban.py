from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.models import Project, Task, ActivityLog, User
from app.schemas.schemas import KanbanMoveRequest, ProjectOut
from app.core.deps import get_current_user

router = APIRouter(prefix="/kanban", tags=["kanban"])


@router.patch("/move", response_model=ProjectOut)
async def move_project(
    payload: KanbanMoveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move a project card to a new Kanban column (status) and optional order position."""
    result = await db.execute(select(Project).where(Project.id == payload.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    old_status = project.status
    project.status = payload.new_status
    if payload.new_order is not None:
        project.kanban_order = payload.new_order

    # Audit log
    log = ActivityLog(
        entity_type="project",
        entity_id=project.id,
        user_id=current_user.id,
        action="moved",
        old_value=old_status.value,
        new_value=payload.new_status.value,
    )
    db.add(log)
    await db.commit()
    await db.refresh(project)

    # Bust the kanban cache so the next board load reflects the move
    from app.api.v1.projects import _kanban_cache
    _kanban_cache.clear()

    result = await db.execute(
        select(Project)
        .options(selectinload(Project.owner), selectinload(Project.tasks).selectinload(Task.assignee),
                 selectinload(Project.insights), selectinload(Project.health_records))
        .where(Project.id == project.id)
    )
    return ProjectOut.model_validate(result.scalar_one())
