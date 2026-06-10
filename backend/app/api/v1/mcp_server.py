"""
Task Planner MCP Server — mounted directly on the FastAPI backend.

Users connect with:
  claude mcp add task-planner https://<backend>/mcp \
    --header "X-Email: you@prospect33.com" \
    --header "X-Password: YourPassword"

The server authenticates each request using those headers, so every
user sees only their own tasks and projects.
"""
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.models import (
    Project, Task, ProjectStatus, PriorityLevel, User,
)
from app.core.security import verify_password

mcp = FastMCP("Task Planner", stateless_http=True)


# ── Auth ──────────────────────────────────────────────────────────────────────

async def _authenticate(email: str | None, password: str | None) -> User | None:
    if not email or not password:
        return None
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not user.password_hash:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


def _auth_error() -> str:
    return (
        "❌ Not authenticated. Connect with your credentials:\n\n"
        "  claude mcp add task-planner https://backend-production-ff8e.up.railway.app/mcp \\\n"
        '    --header "X-Email: you@prospect33.com" \\\n'
        '    --header "X-Password: YourPassword"'
    )


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_my_tasks(
    x_email: Optional[str] = None,
    x_password: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    overdue_only: bool = False,
) -> str:
    """
    List YOUR tasks (assigned to you). Optionally filter by:
    - status: todo / in_progress / blocked / review / done
    - priority: low / medium / high / urgent
    - overdue_only: true to see only past-deadline tasks
    """
    user = await _authenticate(x_email, x_password)
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        query = (
            select(Task)
            .options(selectinload(Task.project))
            .where(Task.assigned_to == user.id, Task.is_completed == False)
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
        return f"No tasks found for {user.name}."

    lines = [f"**{user.name}'s tasks** ({len(tasks)} open):\n"]
    for t in tasks:
        proj = t.project.title if t.project else "?"
        due = f" | Due {t.due_date}" if t.due_date else ""
        flag = " ⚠️ OVERDUE" if (t.due_date and t.due_date < date.today()) else ""
        lines.append(f"• [{t.priority.value.upper()}] {t.title}\n  {proj} | {t.status.value}{due}{flag}")
    return "\n".join(lines)


@mcp.tool()
async def list_my_projects(
    x_email: Optional[str] = None,
    x_password: Optional[str] = None,
) -> str:
    """List projects you own or have tasks assigned in."""
    user = await _authenticate(x_email, x_password)
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        assigned_ids = select(Task.project_id).where(Task.assigned_to == user.id).scalar_subquery()
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.owner))
            .where(
                or_(Project.owner_id == user.id, Project.id.in_(assigned_ids)),
                Project.status != ProjectStatus.done,
            )
            .order_by(Project.updated_at.desc())
        )
        projects = result.scalars().all()

    if not projects:
        return "No active projects found."

    lines = [f"**{user.name}'s projects** ({len(projects)}):\n"]
    for p in projects:
        due = f" | Due {p.due_date}" if p.due_date else ""
        lines.append(f"• [{p.priority.value.upper()}] {p.title} — {p.progress_pct}% done{due}")
    return "\n".join(lines)


@mcp.tool()
async def create_task(
    title: str,
    project_name: str,
    x_email: Optional[str] = None,
    x_password: Optional[str] = None,
    priority: str = "medium",
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    assignee_email: Optional[str] = None,
) -> str:
    """
    Create a task in a project.
    project_name: partial project title match.
    priority: low / medium / high / urgent.
    due_date: YYYY-MM-DD.
    assignee_email: who to assign it to (defaults to you).
    """
    user = await _authenticate(x_email, x_password)
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        proj = (await db.execute(
            select(Project).where(Project.title.ilike(f"%{project_name}%")).limit(1)
        )).scalar_one_or_none()
        if not proj:
            return f"❌ No project matching '{project_name}'."

        assignee_id = user.id
        if assignee_email:
            found = (await db.execute(
                select(User).where(User.email.ilike(f"%{assignee_email}%")).limit(1)
            )).scalar_one_or_none()
            if found:
                assignee_id = found.id

        try:
            pri = PriorityLevel(priority.lower())
        except ValueError:
            pri = PriorityLevel.medium

        parsed_due = None
        if due_date:
            try:
                parsed_due = datetime.strptime(due_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        task = Task(
            title=title,
            description=description,
            status=ProjectStatus.todo,
            priority=pri,
            project_id=proj.id,
            assigned_to=assignee_id,
            due_date=parsed_due,
            created_by=user.id,
        )
        db.add(task)
        await db.commit()

    return f"✅ Created: **{title}** in {proj.title} | {pri.value} priority | due {due_date or 'none'}"


@mcp.tool()
async def create_tasks_bulk(
    tasks_json: str,
    x_email: Optional[str] = None,
    x_password: Optional[str] = None,
) -> str:
    """
    Create multiple tasks at once — ideal after summarising a meeting.
    Pass a JSON array:
    [{"title":"...", "project_name":"...", "priority":"high", "due_date":"2026-06-15", "assignee_email":"..."}]
    """
    user = await _authenticate(x_email, x_password)
    if not user:
        return _auth_error()

    import json
    try:
        items = json.loads(tasks_json)
    except Exception:
        return "❌ Invalid JSON."

    results = []
    for item in items:
        r = await create_task(
            title=item.get("title", "Untitled"),
            project_name=item.get("project_name", "Task Planner App"),
            x_email=x_email,
            x_password=x_password,
            priority=item.get("priority", "medium"),
            description=item.get("description"),
            due_date=item.get("due_date"),
            assignee_email=item.get("assignee_email"),
        )
        results.append(r)

    return f"Created {len(results)} tasks:\n" + "\n".join(results)


@mcp.tool()
async def complete_task(
    task_title_or_id: str,
    x_email: Optional[str] = None,
    x_password: Optional[str] = None,
) -> str:
    """Mark a task as complete by title (partial match) or UUID."""
    user = await _authenticate(x_email, x_password)
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        task = None
        try:
            uid = UUID(task_title_or_id)
            task = (await db.execute(select(Task).where(Task.id == uid))).scalar_one_or_none()
        except ValueError:
            pass
        if not task:
            task = (await db.execute(
                select(Task).where(
                    Task.title.ilike(f"%{task_title_or_id}%"),
                    Task.is_completed == False
                ).limit(1)
            )).scalar_one_or_none()
        if not task:
            return f"❌ No task matching '{task_title_or_id}'."

        task.is_completed = True
        task.status = ProjectStatus.done
        task.completed_at = datetime.utcnow()
        await db.commit()

    return f"✅ Marked complete: **{task.title}**"


@mcp.tool()
async def update_task_status(
    task_title_or_id: str,
    new_status: str,
    x_email: Optional[str] = None,
    x_password: Optional[str] = None,
) -> str:
    """
    Update task status.
    Valid: todo / in_progress / blocked / review / done / cancelled
    """
    user = await _authenticate(x_email, x_password)
    if not user:
        return _auth_error()

    valid = {"todo", "in_progress", "blocked", "review", "done", "cancelled"}
    if new_status not in valid:
        return f"❌ Invalid status. Use: {', '.join(valid)}"

    async with AsyncSessionLocal() as db:
        task = None
        try:
            task = (await db.execute(select(Task).where(Task.id == UUID(task_title_or_id)))).scalar_one_or_none()
        except ValueError:
            pass
        if not task:
            task = (await db.execute(
                select(Task).where(Task.title.ilike(f"%{task_title_or_id}%")).limit(1)
            )).scalar_one_or_none()
        if not task:
            return f"❌ No task matching '{task_title_or_id}'."

        old = task.status.value
        task.status = ProjectStatus(new_status)
        if new_status == "done":
            task.is_completed = True
        await db.commit()

    return f"✅ **{task.title}**: {old} → {new_status}"


@mcp.tool()
async def get_project_summary(
    project_name: str,
    x_email: Optional[str] = None,
    x_password: Optional[str] = None,
) -> str:
    """Get full summary of a project — tasks, progress, blockers."""
    user = await _authenticate(x_email, x_password)
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        proj = (await db.execute(
            select(Project)
            .options(selectinload(Project.tasks).selectinload(Task.assignee), selectinload(Project.owner))
            .where(Project.title.ilike(f"%{project_name}%")).limit(1)
        )).scalar_one_or_none()

    if not proj:
        return f"❌ No project matching '{project_name}'."

    tasks = proj.tasks or []
    open_tasks = [t for t in tasks if not t.is_completed and t.status.value != "cancelled"]
    done_tasks = [t for t in tasks if t.is_completed]
    overdue = [t for t in open_tasks if t.due_date and t.due_date < date.today()]

    lines = [
        f"**{proj.title}**",
        f"Status: {proj.status.value} | Priority: {proj.priority.value} | {proj.progress_pct}% done",
        f"Owner: {proj.owner.name if proj.owner else 'None'} | Due: {proj.due_date or 'not set'}",
        f"Tasks: {len(done_tasks)}/{len(tasks)} done | {len(overdue)} overdue",
    ]
    if proj.blockers:
        lines.append(f"\n⚠️ BLOCKERS: {proj.blockers}")
    if open_tasks:
        lines.append(f"\nOpen tasks:")
        for t in open_tasks[:10]:
            who = t.assignee.name.split()[0] if t.assignee else "?"
            due = f" due {t.due_date}" if t.due_date else ""
            lines.append(f"  • [{t.priority.value}] {t.title} ({who}{due})")
    return "\n".join(lines)
