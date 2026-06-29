from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
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
    query = select(Task).options(selectinload(Task.assignee))
    if project_id:
        query = query.where(Task.project_id == project_id)
    if assigned_to:
        query = query.where(Task.assigned_to == assigned_to)
    result = await db.execute(query.order_by(Task.kanban_order, Task.created_at))
    return [TaskOut.model_validate(t) for t in result.scalars().all()]


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    # No task is left unassigned: default the assignee to its creator.
    if data.get("assigned_to") is None:
        data["assigned_to"] = current_user.id
    task = Task(**data, created_by=current_user.id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    result = await db.execute(select(Task).options(selectinload(Task.assignee)).where(Task.id == task.id))
    return TaskOut.model_validate(result.scalar_one())


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

    update_data = payload.model_dump(exclude_unset=True)
    if "is_completed" in update_data and update_data["is_completed"] and not task.is_completed:
        update_data["completed_at"] = datetime.utcnow()

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    result = await db.execute(select(Task).options(selectinload(Task.assignee)).where(Task.id == task_id))
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
    await db.execute(delete(Task).where(Task.id == task_id))
    await db.commit()
