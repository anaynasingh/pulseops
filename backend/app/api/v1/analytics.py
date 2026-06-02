from datetime import datetime, timedelta
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.models import (
    Project, Task, ActivityLog, AIInsight, User,
    ProjectHealth, ProjectStatus, PriorityLevel
)
from app.schemas.schemas import DashboardStats, ProjectOut, ActivityLogOut, AIInsightOut, ProjectHealthOut
from app.core.deps import get_current_user

_PRIORITY_ORDER_SQL = text(
    "CASE projects.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END"
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    # Counts
    total_res = await db.execute(select(func.count()).select_from(Project))
    total = total_res.scalar()

    active_res = await db.execute(
        select(func.count()).select_from(Project).where(
            Project.status.in_([ProjectStatus.in_progress, ProjectStatus.review])
        )
    )
    active = active_res.scalar()

    blocked_res = await db.execute(
        select(func.count()).select_from(Project).where(Project.status == ProjectStatus.blocked)
    )
    blocked = blocked_res.scalar()

    done_res = await db.execute(
        select(func.count()).select_from(Project).where(
            Project.status == ProjectStatus.done,
            Project.updated_at >= week_ago
        )
    )
    done_week = done_res.scalar()

    intake_res = await db.execute(
        select(func.count()).select_from(Project).where(Project.status == ProjectStatus.intake)
    )
    intake = intake_res.scalar()

    overdue_res = await db.execute(
        select(func.count()).select_from(Project).where(
            Project.due_date < now.date(),
            Project.status.notin_([ProjectStatus.done])
        )
    )
    overdue = overdue_res.scalar()

    # Recent activity (last 20)
    activity_res = await db.execute(
        select(ActivityLog)
        .options(selectinload(ActivityLog.user))
        .order_by(ActivityLog.created_at.desc())
        .limit(20)
    )
    recent_activity = [ActivityLogOut.model_validate(a) for a in activity_res.scalars().all()]

    # High priority projects (not done)
    hp_res = await db.execute(
        select(Project)
        .options(selectinload(Project.owner), selectinload(Project.tasks).selectinload(Task.assignee),
                 selectinload(Project.insights), selectinload(Project.health_records))
        .where(
            Project.priority.in_([PriorityLevel.high, PriorityLevel.urgent]),
            Project.status.notin_([ProjectStatus.done])
        )
        .order_by(_PRIORITY_ORDER_SQL, Project.due_date)
        .limit(5)
    )
    high_priority = [ProjectOut.model_validate(p) for p in hp_res.scalars().all()]

    # Stale projects (not updated in 7+ days, not done)
    stale_res = await db.execute(
        select(Project)
        .options(selectinload(Project.owner), selectinload(Project.tasks).selectinload(Task.assignee),
                 selectinload(Project.insights), selectinload(Project.health_records))
        .where(
            Project.updated_at < week_ago,
            Project.status.notin_([ProjectStatus.done, ProjectStatus.potential])
        )
        .order_by(Project.updated_at)
        .limit(5)
    )
    stale = [ProjectOut.model_validate(p) for p in stale_res.scalars().all()]

    # AI insights (recent, undismissed)
    insights_res = await db.execute(
        select(AIInsight)
        .where(AIInsight.is_dismissed == False)
        .order_by(AIInsight.created_at.desc())
        .limit(10)
    )
    insights = [AIInsightOut.model_validate(i) for i in insights_res.scalars().all()]

    # Team workload (count projects per owner)
    workload_res = await db.execute(
        select(User.name, User.id, func.count(Project.id).label("count"))
        .join(Project, Project.owner_id == User.id)
        .where(Project.status.notin_([ProjectStatus.done]))
        .group_by(User.id, User.name)
        .order_by(func.count(Project.id).desc())
    )
    team_workload = [
        {"user_id": str(row.id), "name": row.name, "project_count": row.count}
        for row in workload_res
    ]

    return DashboardStats(
        total_projects=total,
        active_projects=active,
        blocked_projects=blocked,
        done_this_week=done_week,
        intake_queue=intake,
        overdue_projects=overdue,
        team_workload=team_workload,
        recent_activity=recent_activity,
        high_priority_projects=high_priority,
        stale_projects=stale,
        ai_insights=insights,
    )


@router.get("/gantt", response_model=dict)
async def get_gantt_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all projects with tasks structured for Gantt rendering."""
    today = datetime.utcnow().date()

    projects_res = await db.execute(
        select(Project)
        .options(
            selectinload(Project.tasks).selectinload(Task.assignee),
            selectinload(Project.owner),
        )
        .order_by(Project.created_at)
    )
    projects = projects_res.scalars().all()

    items = []
    all_dates = []

    for project in projects:
        # Project date range
        proj_start = project.created_at.date() if project.created_at else today
        proj_end = project.due_date if project.due_date else (proj_start + timedelta(days=30))

        # Compute progress
        tasks = project.tasks or []
        if tasks:
            completed = sum(1 for t in tasks if t.is_completed)
            progress = int((completed / len(tasks)) * 100)
        else:
            progress = project.progress_pct

        subtasks = []
        for task in tasks:
            t_start = proj_start
            t_end = task.due_date if task.due_date else proj_end
            subtasks.append({
                "id": str(task.id),
                "title": task.title,
                "type": "task",
                "assignee": task.assignee.name if task.assignee else None,
                "start_date": t_start.isoformat(),
                "end_date": t_end.isoformat(),
                "is_completed": task.is_completed,
                "priority": task.priority.value if hasattr(task.priority, "value") else task.priority,
            })
            all_dates.extend([t_start, t_end])

        items.append({
            "id": str(project.id),
            "title": project.title,
            "type": "project",
            "status": project.status.value if hasattr(project.status, "value") else project.status,
            "priority": project.priority.value if hasattr(project.priority, "value") else project.priority,
            "start_date": proj_start.isoformat(),
            "end_date": proj_end.isoformat(),
            "progress": progress,
            "subtasks": subtasks,
        })
        all_dates.extend([proj_start, proj_end])

    if all_dates:
        min_date = (min(all_dates) - timedelta(days=7)).isoformat()
        max_date = (max(all_dates) + timedelta(days=7)).isoformat()
    else:
        min_date = today.isoformat()
        max_date = (today + timedelta(days=30)).isoformat()

    return {"items": items, "min_date": min_date, "max_date": max_date}


@router.get("/health/{project_id}", response_model=ProjectHealthOut)
async def get_project_health(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProjectHealth)
        .where(ProjectHealth.project_id == project_id)
        .order_by(ProjectHealth.evaluated_at.desc())
        .limit(1)
    )
    health = result.scalar_one_or_none()
    if not health:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No health record found")
    return ProjectHealthOut.model_validate(health)
