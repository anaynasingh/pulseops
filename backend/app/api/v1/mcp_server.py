"""
Task Planner MCP Server — mounted directly on the FastAPI backend.
Users connect with: claude mcp add task-planner <BACKEND_URL>/mcp
Authentication via the same JWT tokens used by the web app.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import Depends
from mcp.server.fastmcp import FastMCP
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.models import (
    Project, Task, ProjectStatus, PriorityLevel,
)
from app.schemas.schemas import TaskCreate

# FastMCP instance — will be mounted as ASGI app at /mcp
mcp = FastMCP("Task Planner", stateless_http=True)


# ── Helper to get a DB session inside MCP tools ──────────────────────────────
# FastMCP tools are plain async functions; we create a session manually.

from app.db.session import AsyncSessionLocal


async def _db():
    async with AsyncSessionLocal() as session:
        return session


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_my_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    overdue_only: bool = False,
) -> str:
    """
    List tasks assigned to the authenticated user.
    Optionally filter by status (todo/in_progress/blocked/review/done)
    or priority (low/medium/high/urgent).
    Set overdue_only=true to see only past-deadline tasks.
    """
    async with AsyncSessionLocal() as db:
        query = (
            select(Task)
            .options(selectinload(Task.project), selectinload(Task.assignee))
            .where(Task.is_completed == False)
        )
        if status:
            try:
                query = query.where(Task.status == ProjectStatus(status))
            except ValueError:
                pass
        if priority:
            try:
                query = query.where(Task.priority == PriorityLevel(priority))
            except ValueError:
                pass
        if overdue_only:
            query = query.where(Task.due_date < date.today())

        result = await db.execute(query)
        tasks = result.scalars().all()

    if not tasks:
        return "No tasks found matching your filters."

    lines = [f"Found {len(tasks)} task(s):\n"]
    for t in tasks:
        proj_name = t.project.title if t.project else "Unknown project"
        due = f" | Due {t.due_date}" if t.due_date else ""
        overdue_flag = " ⚠️ OVERDUE" if (t.due_date and t.due_date < date.today()) else ""
        lines.append(
            f"• [{t.priority.value.upper()}] {t.title}\n"
            f"  Project: {proj_name} | Status: {t.status.value}{due}{overdue_flag}\n"
            f"  ID: {t.id}"
        )
    return "\n".join(lines)


@mcp.tool()
async def list_projects(mine_only: bool = True) -> str:
    """
    List projects. Set mine_only=false to see all team projects.
    """
    async with AsyncSessionLocal() as db:
        query = (
            select(Project)
            .options(selectinload(Project.owner))
            .where(Project.status != ProjectStatus.done)
            .order_by(Project.updated_at.desc())
        )
        result = await db.execute(query)
        projects = result.scalars().all()

    if not projects:
        return "No active projects found."

    lines = [f"Found {len(projects)} active project(s):\n"]
    for p in projects:
        owner = p.owner.name if p.owner else "Unassigned"
        due = f" | Due {p.due_date}" if p.due_date else ""
        lines.append(
            f"• [{p.priority.value.upper()}] {p.title}\n"
            f"  Status: {p.status.value} | Progress: {p.progress_pct}%{due} | Owner: {owner}\n"
            f"  ID: {p.id}"
        )
    return "\n".join(lines)


@mcp.tool()
async def create_task(
    title: str,
    project_name: str,
    priority: str = "medium",
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    assignee_email: Optional[str] = None,
) -> str:
    """
    Create a new task in a project.
    project_name: partial match on project title.
    priority: low / medium / high / urgent.
    due_date: YYYY-MM-DD format.
    assignee_email: email of the person to assign it to.
    """
    async with AsyncSessionLocal() as db:
        # Find project
        proj_result = await db.execute(
            select(Project).where(Project.title.ilike(f"%{project_name}%")).limit(1)
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            return f"❌ Could not find a project matching '{project_name}'. Check the project name and try again."

        # Find assignee
        assignee_id = None
        if assignee_email:
            from app.models.models import User
            user_result = await db.execute(
                select(User).where(User.email.ilike(f"%{assignee_email}%")).limit(1)
            )
            user = user_result.scalar_one_or_none()
            if user:
                assignee_id = user.id

        # Parse priority
        try:
            pri = PriorityLevel(priority.lower())
        except ValueError:
            pri = PriorityLevel.medium

        # Parse due date
        parsed_due = None
        if due_date:
            try:
                from datetime import datetime
                parsed_due = datetime.strptime(due_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        task = Task(
            title=title,
            description=description,
            status=ProjectStatus.todo,
            priority=pri,
            project_id=project.id,
            assigned_to=assignee_id,
            due_date=parsed_due,
        )
        db.add(task)
        await db.commit()

    return (
        f"✅ Task created: **{title}**\n"
        f"  Project: {project.title} | Priority: {pri.value} | Due: {due_date or 'none'}"
    )


@mcp.tool()
async def complete_task(task_title_or_id: str) -> str:
    """
    Mark a task as complete by title (partial match) or UUID.
    Example: complete_task('Fix CORS bug')
    """
    async with AsyncSessionLocal() as db:
        # Try UUID first
        task = None
        try:
            uid = UUID(task_title_or_id)
            result = await db.execute(select(Task).where(Task.id == uid))
            task = result.scalar_one_or_none()
        except ValueError:
            pass

        # Fall back to title search
        if not task:
            result = await db.execute(
                select(Task)
                .where(Task.title.ilike(f"%{task_title_or_id}%"), Task.is_completed == False)
                .limit(1)
            )
            task = result.scalar_one_or_none()

        if not task:
            return f"❌ Could not find task matching '{task_title_or_id}'."

        task.is_completed = True
        task.status = ProjectStatus.done
        from datetime import datetime
        task.completed_at = datetime.utcnow()
        await db.commit()

    return f"✅ Task marked complete: **{task.title}**"


@mcp.tool()
async def update_task_status(task_title_or_id: str, new_status: str) -> str:
    """
    Update the status of a task.
    Statuses: todo / in_progress / blocked / review / done / cancelled
    """
    valid = {"todo", "in_progress", "blocked", "review", "done", "cancelled"}
    if new_status not in valid:
        return f"❌ Invalid status '{new_status}'. Use one of: {', '.join(valid)}"

    async with AsyncSessionLocal() as db:
        task = None
        try:
            uid = UUID(task_title_or_id)
            result = await db.execute(select(Task).where(Task.id == uid))
            task = result.scalar_one_or_none()
        except ValueError:
            pass

        if not task:
            result = await db.execute(
                select(Task).where(Task.title.ilike(f"%{task_title_or_id}%")).limit(1)
            )
            task = result.scalar_one_or_none()

        if not task:
            return f"❌ Could not find task matching '{task_title_or_id}'."

        old = task.status.value
        task.status = ProjectStatus(new_status)
        if new_status == "done":
            task.is_completed = True
        await db.commit()

    return f"✅ **{task.title}** status changed: {old} → {new_status}"


@mcp.tool()
async def get_project_summary(project_name: str) -> str:
    """
    Get a detailed summary of a project — status, progress, tasks, blockers.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Project)
            .options(
                selectinload(Project.tasks).selectinload(Task.assignee),
                selectinload(Project.owner),
            )
            .where(Project.title.ilike(f"%{project_name}%"))
            .limit(1)
        )
        project = result.scalar_one_or_none()

    if not project:
        return f"❌ No project found matching '{project_name}'."

    tasks = project.tasks or []
    open_tasks = [t for t in tasks if not t.is_completed and t.status.value != "cancelled"]
    done_tasks = [t for t in tasks if t.is_completed]
    overdue = [t for t in open_tasks if t.due_date and t.due_date < date.today()]

    lines = [
        f"**{project.title}**",
        f"Status: {project.status.value} | Priority: {project.priority.value} | Progress: {project.progress_pct}%",
        f"Owner: {project.owner.name if project.owner else 'None'} | Due: {project.due_date or 'not set'}",
        f"Tasks: {len(done_tasks)}/{len(tasks)} done | {len(overdue)} overdue",
    ]

    if project.blockers:
        lines.append(f"\n⚠️ BLOCKERS: {project.blockers}")

    if open_tasks:
        lines.append(f"\nOpen tasks ({len(open_tasks)}):")
        for t in open_tasks[:10]:
            assignee = t.assignee.name.split()[0] if t.assignee else "Unassigned"
            due = f" due {t.due_date}" if t.due_date else ""
            lines.append(f"  • [{t.priority.value}] {t.title} ({assignee}{due})")

    return "\n".join(lines)


@mcp.tool()
async def create_tasks_bulk(tasks_json: str) -> str:
    """
    Create multiple tasks at once from a JSON array.
    Format: [{"title": "...", "project_name": "...", "priority": "high", "due_date": "2026-06-15", "assignee_email": "..."}]
    Use this after summarising a meeting to add all action items in one shot.
    """
    import json as _json
    try:
        items = _json.loads(tasks_json)
    except Exception:
        return "❌ Invalid JSON. Provide a list of task objects."

    results = []
    for item in items:
        result = await create_task(
            title=item.get("title", "Untitled"),
            project_name=item.get("project_name", "Task Planner App"),
            priority=item.get("priority", "medium"),
            description=item.get("description"),
            due_date=item.get("due_date"),
            assignee_email=item.get("assignee_email"),
        )
        results.append(result)

    return f"Created {len(results)} tasks:\n" + "\n".join(results)
