from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.models import Task, User, ActivityLog
from app.schemas.schemas import TaskCreate, TaskUpdate, TaskOut
from app.core.deps import get_current_user, get_db_for_user, require_writer

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _log_activity(db: AsyncSession, task_id, user_id, action: str, new_val: str = None):
    """Record a task action in the activity feed (mirrors projects._log_activity)."""
    db.add(ActivityLog(
        entity_type="task",
        entity_id=task_id,
        user_id=user_id,
        action=action,
        new_value=new_val,
    ))


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


@router.get("/day")
async def day_view(
    start: datetime = Query(..., description="Local day start as ISO 8601 datetime"),
    end: datetime = Query(..., description="Local day end (exclusive) as ISO 8601 datetime"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Franklin Covey day view: the current user's tasks scheduled into [start, end)
    plus their unscheduled incomplete tasks."""
    from datetime import timezone, timedelta

    # Coerce naive datetimes to UTC (frontend sends tz-aware ISO; this is a guard)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    if end <= start:
        raise HTTPException(status_code=422, detail="end must be after start")
    if (end - start) > timedelta(hours=48):
        raise HTTPException(status_code=422, detail="range too large (max 48h)")

    base = select(Task).options(selectinload(Task.assignee), selectinload(Task.project))

    scheduled_res = await db.execute(
        base.where(
            Task.assigned_to == current_user.id,
            Task.scheduled_at >= start,
            Task.scheduled_at < end,
        ).order_by(Task.scheduled_at)
    )
    unscheduled_res = await db.execute(
        base.where(
            Task.assigned_to == current_user.id,
            Task.is_completed == False,
            Task.scheduled_at.is_(None),
        ).order_by(
            text("CASE tasks.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"),
            Task.created_at,
        )
    )

    return {
        "scheduled": [TaskOut.model_validate(t) for t in scheduled_res.scalars().all()],
        "unscheduled": [TaskOut.model_validate(t) for t in unscheduled_res.scalars().all()],
    }


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(require_writer),
):
    data = payload.model_dump(exclude_unset=True)
    # Resolve an email/name assignee to a user id (so callers can assign without
    # knowing the UUID). Explicit assigned_to wins if both are given.
    assignee_str = data.pop("assignee", None)
    if assignee_str and not data.get("assigned_to"):
        assignee_str = assignee_str.strip()
        res = await db.execute(select(User).where(User.email.ilike(assignee_str)))
        user = res.scalar_one_or_none()
        if user is None:
            res = await db.execute(
                select(User).where(User.name.ilike(f"%{assignee_str}%")).limit(2)
            )
            matches = res.scalars().all()
            if len(matches) == 1:
                user = matches[0]
            elif len(matches) > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Assignee '{assignee_str}' matches multiple users — use their exact email.",
                )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not find a user matching assignee '{assignee_str}'. Use their exact email.",
            )
        data["assigned_to"] = user.id
    # No task is left unassigned: default the assignee to its creator.
    if "assigned_to" not in data or data["assigned_to"] is None:
        data["assigned_to"] = current_user.id
    task = Task(**data, created_by=current_user.id)
    db.add(task)
    await db.flush()  # populate task.id before logging
    await _log_activity(db, task.id, current_user.id, "task_created", task.title)
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
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(require_writer),
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
    if "assigned_to" in update_data and update_data["assigned_to"] != task.assigned_to:
        update_data["last_reminded_at"] = None

    for field, value in update_data.items():
        setattr(task, field, value)

    action = "task_completed" if update_data.get("is_completed") is True else "task_updated"
    await _log_activity(db, task.id, current_user.id, action, task.title)
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
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(require_writer),
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

    title = task.title
    await db.delete(task)
    await _log_activity(db, task_id, current_user.id, "task_deleted", title)
    await db.commit()
