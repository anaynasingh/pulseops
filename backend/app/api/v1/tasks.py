from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.models import Task, User
from app.schemas.schemas import TaskCreate, TaskUpdate, TaskOut
from app.core.deps import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=List[TaskOut])
async def list_tasks(
    project_id: Optional[UUID] = Query(None),
    assigned_to: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import or_
    query = select(Task).options(selectinload(Task.assignee), selectinload(Task.project))
    if project_id:
        query = query.where(Task.project_id == project_id)
    if assigned_to:
        query = query.where(Task.assigned_to == assigned_to)
    # Privacy filter: private tasks only visible to assignee or creator
    query = query.where(
        or_(
            Task.is_private == False,
            Task.assigned_to == current_user.id,
            Task.created_by == current_user.id,
        )
    )
    result = await db.execute(query.order_by(Task.kanban_order, Task.created_at))
    return [TaskOut.model_validate(t) for t in result.scalars().all()]


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(**payload.model_dump(), created_by=current_user.id)
    db.add(task)
    await db.commit()
    result = await db.execute(
        select(Task).options(selectinload(Task.assignee), selectinload(Task.project)).where(Task.id == task.id)
    )
    return TaskOut.model_validate(result.scalar_one())


def _can_edit_task(task: Task, user: User) -> bool:
    """Guardrail: only assignee or creator can edit/delete a task."""
    return (
        task.assigned_to == user.id or
        task.created_by == user.id or
        user.role.value == "admin"   # admins can edit anything
    )


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not _can_edit_task(task, current_user):
        raise HTTPException(
            status_code=403,
            detail=f"You can only edit tasks assigned to you or created by you. This task belongs to someone else."
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "is_completed" in update_data and update_data["is_completed"] and not task.is_completed:
        update_data["completed_at"] = datetime.utcnow()

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()

    # Auto-recalculate project progress_pct whenever a task completion changes
    if "is_completed" in update_data or "status" in update_data:
        from app.models.models import Project
        from sqlalchemy import func
        total = (await db.execute(
            select(func.count()).select_from(Task).where(Task.project_id == task.project_id)
        )).scalar() or 0
        done = (await db.execute(
            select(func.count()).select_from(Task).where(
                Task.project_id == task.project_id,
                Task.is_completed == True,
            )
        )).scalar() or 0
        new_pct = int((done / total) * 100) if total > 0 else 0
        await db.execute(
            select(Project).where(Project.id == task.project_id)
        )
        proj_result = await db.execute(select(Project).where(Project.id == task.project_id))
        proj = proj_result.scalar_one_or_none()
        if proj:
            proj.progress_pct = new_pct
            await db.commit()

    result = await db.execute(
        select(Task).options(selectinload(Task.assignee), selectinload(Task.project)).where(Task.id == task_id)
    )
    return TaskOut.model_validate(result.scalar_one())


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not _can_edit_task(task, current_user):
        raise HTTPException(
            status_code=403,
            detail="You can only delete tasks assigned to you or created by you."
        )

    await db.delete(task)
    await db.commit()
