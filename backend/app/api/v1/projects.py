from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.models import Project, Task, ActivityLog, ProjectStatus, PriorityLevel, User
from app.schemas.schemas import ProjectCreate, ProjectUpdate, ProjectOut
from app.core.deps import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


async def _log_activity(db: AsyncSession, entity_id: UUID, user_id: UUID,
                        action: str, old_val: str = None, new_val: str = None):
    log = ActivityLog(
        entity_type="project",
        entity_id=entity_id,
        user_id=user_id,
        action=action,
        old_value=old_val,
        new_value=new_val,
    )
    db.add(log)


@router.get("/", response_model=List[ProjectOut])
async def list_projects(
    status: Optional[ProjectStatus] = Query(None),
    priority: Optional[PriorityLevel] = Query(None),
    owner_id: Optional[UUID] = Query(None),
    team_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None, description="Keyword search on title/description"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Project)
        .options(
            selectinload(Project.owner),
            selectinload(Project.tasks).selectinload(Task.assignee),
            selectinload(Project.insights),
            selectinload(Project.health_records),
        )
        .order_by(Project.kanban_order, Project.updated_at.desc())
    )

    if status:
        query = query.where(Project.status == status)
    if priority:
        query = query.where(Project.priority == priority)
    if owner_id:
        # Show projects the user owns OR has tasks assigned to them in
        assigned_project_ids = select(Task.project_id).where(
            Task.assigned_to == owner_id
        ).scalar_subquery()
        query = query.where(
            or_(
                Project.owner_id == owner_id,
                Project.id.in_(assigned_project_ids),
            )
        )
    if team_id:
        query = query.where(Project.team_id == team_id)
    if q:
        query = query.where(
            or_(
                Project.title.ilike(f"%{q}%"),
                Project.description.ilike(f"%{q}%"),
            )
        )

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    projects = result.scalars().all()
    return [ProjectOut.model_validate(p) for p in projects]


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(**payload.model_dump(), created_by=current_user.id)
    db.add(project)
    await db.flush()  # get ID before commit
    await _log_activity(db, project.id, current_user.id, "created")
    await db.commit()
    await db.refresh(project)

    # Re-fetch with relationships
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.owner), selectinload(Project.tasks).selectinload(Task.assignee),
                 selectinload(Project.insights), selectinload(Project.health_records))
        .where(Project.id == project.id)
    )
    return ProjectOut.model_validate(result.scalar_one())


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.owner), selectinload(Project.tasks).selectinload(Task.assignee),
                 selectinload(Project.insights), selectinload(Project.health_records))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        old_val = str(getattr(project, field)) if field in ("status", "priority") else None
        setattr(project, field, value)
        if field in ("status", "priority"):
            await _log_activity(db, project.id, current_user.id,
                                f"{field}_changed", old_val, str(value))

    await db.commit()
    await db.refresh(project)

    result = await db.execute(
        select(Project)
        .options(selectinload(Project.owner), selectinload(Project.tasks).selectinload(Task.assignee),
                 selectinload(Project.insights), selectinload(Project.health_records))
        .where(Project.id == project_id)
    )
    return ProjectOut.model_validate(result.scalar_one())


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
