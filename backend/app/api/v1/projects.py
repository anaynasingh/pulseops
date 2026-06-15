from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
import time
from app.db.session import get_db
from app.models.models import Project, Task, ActivityLog, ProjectStatus, PriorityLevel, User
from app.schemas.schemas import ProjectCreate, ProjectUpdate, ProjectOut, ProjectKanbanOut, UserOut
from app.core.deps import get_current_user, get_db_for_user, require_writer

router = APIRouter(prefix="/projects", tags=["projects"])


def _can_edit_project(project: Project, user: User) -> bool:
    """Hard control: only owner, creator, or admin may mutate a project."""
    return (
        project.owner_id == user.id or
        project.created_by == user.id or
        user.role.value == "admin"
    )

# ── Simple in-memory cache for kanban endpoint ────────────────────────────────
# Supabase is in Sydney — each round trip adds 200-400ms latency.
# Cache the kanban board for 30 seconds so navigating back is instant.
_kanban_cache: dict = {}   # key: (owner_id, status, priority) → (timestamp, data)
_CACHE_TTL = 30             # seconds


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


@router.get("/kanban", response_model=List[ProjectKanbanOut])
async def list_projects_kanban(
    status: Optional[ProjectStatus] = Query(None),
    priority: Optional[PriorityLevel] = Query(None),
    owner_id: Optional[UUID] = Query(None),
    limit: int = Query(200, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Slim endpoint for the Kanban board — loads only project metadata, no nested relations."""
    cache_key = (str(owner_id), str(status), str(priority))
    cached = _kanban_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return cached[1]   # serve from cache — instant

    query = (
        select(Project)
        .options(selectinload(Project.owner))  # owner name needed for Kanban card
        .order_by(Project.kanban_order, Project.updated_at.desc())
    )
    if status:
        query = query.where(Project.status == status)
    if priority:
        query = query.where(Project.priority == priority)
    if owner_id:
        assigned_ids = select(Task.project_id).where(Task.assigned_to == owner_id).scalar_subquery()
        query = query.where(or_(Project.owner_id == owner_id, Project.id.in_(assigned_ids)))
    query = query.limit(limit)
    result = await db.execute(query)
    raw_projects = result.scalars().all()

    if not raw_projects:
        _kanban_cache[cache_key] = (time.time(), [])
        return []

    # Batch-load ALL distinct assignees per project in ONE extra query
    # Far cheaper than selectinload(tasks) which loads full task data
    project_ids = [p.id for p in raw_projects]
    assignee_rows = (await db.execute(
        select(Task.project_id, User)
        .join(User, User.id == Task.assigned_to)
        .where(Task.project_id.in_(project_ids), Task.assigned_to.isnot(None))
    )).all()

    from collections import defaultdict
    assignees_by_project: dict = defaultdict(dict)
    for proj_id, user in assignee_rows:
        assignees_by_project[proj_id][user.id] = UserOut.model_validate(user)

    # Build final output
    projects = []
    for p in raw_projects:
        item = ProjectKanbanOut.model_validate(p)
        item.assignees = list(assignees_by_project.get(p.id, {}).values())
        projects.append(item)

    _kanban_cache[cache_key] = (time.time(), projects)
    return projects


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
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(require_writer),
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
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(require_writer),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not _can_edit_project(project, current_user):
        raise HTTPException(
            status_code=403,
            detail="You can only edit projects you own or created."
        )

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
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(require_writer),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not _can_edit_project(project, current_user):
        raise HTTPException(
            status_code=403,
            detail="You can only delete projects you own or created."
        )

    await db.delete(project)
    await db.commit()
