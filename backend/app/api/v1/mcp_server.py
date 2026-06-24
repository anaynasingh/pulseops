"""
Task Planner MCP Server.

Connect with:
  claude mcp add task-planner --transport sse <backend>/mcp/sse \
    --header "X-Token: <your-jwt-from-pulseops>"

MCPHeaderMiddleware (in main.py) captures the X-Token header into a ContextVar
before every request. Tools read auth from ContextVars — no credentials
needed as tool parameters.
"""
from contextvars import ContextVar
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.models import (
    Project, Task, ProjectStatus, PriorityLevel, User, TranscriptSearchLog,
)
from app.core.security import decode_token

mcp = FastMCP("Task Planner")

# Set by MCPHeaderMiddleware in main.py before every request
mcp_email_var: ContextVar[Optional[str]] = ContextVar("mcp_email", default=None)
mcp_password_var: ContextVar[Optional[str]] = ContextVar("mcp_password", default=None)
mcp_token_var: ContextVar[Optional[str]] = ContextVar("mcp_token", default=None)


async def _authenticate() -> User | None:
    token = mcp_token_var.get()
    if not token:
        return None

    # Try JWT first
    payload = decode_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                return user if user and user.is_active else None

    # Try long-lived API key
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.api_key == token))
        user = result.scalar_one_or_none()
        return user if user and user.is_active else None


def _auth_error() -> str:
    return (
        "❌ Not authenticated. Copy your token from PulseOps (Settings → MCP Token), then run:\n\n"
        "  claude mcp remove task-planner\n"
        "  claude mcp add task-planner --transport sse \\\n"
        "    https://backend-production-ff8e.up.railway.app/mcp/sse \\\n"
        '    --header "X-Token: <your-token>"\n\n'
        "Then restart Claude Code."
    )


@mcp.tool()
async def list_my_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    overdue_only: bool = False,
) -> str:
    """
    List YOUR tasks (assigned to you). Filter by:
    status: todo/in_progress/blocked/review/done
    priority: low/medium/high/urgent
    overdue_only: true for past-deadline only
    """
    user = await _authenticate()
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
        return f"No open tasks for {user.name}."

    lines = [f"**{user.name}'s tasks** ({len(tasks)} open):\n"]
    for t in tasks:
        proj = t.project.title if t.project else "?"
        due = f" | Due {t.due_date}" if t.due_date else ""
        flag = " ⚠️ OVERDUE" if (t.due_date and t.due_date < date.today()) else ""
        lines.append(f"• [{t.priority.value.upper()}] {t.title}\n  {proj} | {t.status.value}{due}{flag}")
    return "\n".join(lines)


@mcp.tool()
async def list_my_projects() -> str:
    """List projects you own or have tasks assigned in."""
    user = await _authenticate()
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        assigned_ids = select(Task.project_id).where(Task.assigned_to == user.id).scalar_subquery()
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.owner))
            .where(or_(Project.owner_id == user.id, Project.id.in_(assigned_ids)),
                   Project.status != ProjectStatus.done)
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
    priority: str = "medium",
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    assignee_email: Optional[str] = None,
) -> str:
    """Create a task. project_name=partial match. priority=low/medium/high/urgent. due_date=YYYY-MM-DD."""
    user = await _authenticate()
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

        task = Task(title=title, description=description, status=ProjectStatus.todo,
                    priority=pri, project_id=proj.id, assigned_to=assignee_id,
                    due_date=parsed_due, created_by=user.id)
        db.add(task)
        await db.commit()

    return f"✅ Created: **{title}** in {proj.title} | {pri.value} | due {due_date or 'none'}"


@mcp.tool()
async def create_tasks_bulk(tasks_json: str, skip_dedup: bool = False) -> str:
    """
    Create multiple tasks at once from a JSON array.
    [{"title":"...", "project_name":"...", "priority":"high", "due_date":"2026-06-15", "assignee_email":"..."}]
    Automatically skips duplicates (>=85% match). Set skip_dedup=True to create all.
    """
    user = await _authenticate()
    if not user:
        return _auth_error()

    import json as _json
    try:
        items = _json.loads(tasks_json)
    except Exception:
        return "❌ Invalid JSON."

    if not items:
        return "No tasks to create."

    skipped = []
    to_create = items[:]

    if not skip_dedup:
        try:
            from app.api.v1.ai import _DEDUPE_SYSTEM
            from app.services.ai_service import client as _client, MODEL as _MODEL
            async with AsyncSessionLocal() as db:
                assigned_ids = select(Task.project_id).where(Task.assigned_to == user.id).scalar_subquery()
                existing = (await db.execute(
                    select(Task).where(Task.is_completed == False, Task.status != "cancelled",
                                       Task.project_id.in_(assigned_ids)).limit(80)
                )).scalars().all()
            if existing:
                existing_list = "\n".join([f'- [{t.id}] "{t.title}" | {t.status.value}' for t in existing])
                proposed_list = "\n".join([f'- "{item.get("title", "")}"' for item in items])
                resp = await _client.chat.completions.create(
                    model=_MODEL,
                    messages=[{"role": "system", "content": _DEDUPE_SYSTEM},
                              {"role": "user", "content": f"EXISTING:\n{existing_list}\n\nPROPOSED:\n{proposed_list}"}],
                    response_format={"type": "json_object"}, temperature=0.1,
                )
                raw = _json.loads(resp.choices[0].message.content)
                matches = raw.get("matches", raw) if isinstance(raw, dict) else raw
                skip_titles = {m["proposed_title"] for m in matches
                               if m.get("match_type") == "duplicate" and float(m.get("confidence", 0)) >= 0.85}
                skipped = [f'  ↩ Skipped "{m["proposed_title"]}" — {m.get("suggestion", "already exists")}'
                           for m in matches if m["proposed_title"] in skip_titles]
                to_create = [item for item in items if item.get("title") not in skip_titles]
        except Exception as e:
            skipped.append(f"  ⚠ Dedup failed ({e})")

    results = []
    for item in to_create:
        r = await create_task(
            title=item.get("title", "Untitled"), project_name=item.get("project_name", "Task Planner App"),
            priority=item.get("priority", "medium"), description=item.get("description"),
            due_date=item.get("due_date"), assignee_email=item.get("assignee_email"),
        )
        results.append(r)

    lines = []
    if results:
        lines.append(f"✅ Created {len(results)} task(s):\n" + "\n".join(f"  {r}" for r in results))
    if skipped:
        lines.append(f"\n⏭ Skipped {len(skipped)} duplicate(s):\n" + "\n".join(skipped))
    return "\n".join(lines) if lines else "Nothing to create."


@mcp.tool()
async def complete_task(task_title_or_id: str) -> str:
    """Mark a task complete by title (partial match) or UUID."""
    user = await _authenticate()
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        task = None
        try:
            task = (await db.execute(select(Task).where(Task.id == UUID(task_title_or_id)))).scalar_one_or_none()
        except ValueError:
            pass
        if not task:
            task = (await db.execute(
                select(Task).where(Task.title.ilike(f"%{task_title_or_id}%"), Task.is_completed == False).limit(1)
            )).scalar_one_or_none()
        if not task:
            return f"❌ No task matching '{task_title_or_id}'."
        task.is_completed = True
        task.status = ProjectStatus.done
        task.completed_at = datetime.utcnow()
        await db.commit()
    return f"✅ Marked complete: **{task.title}**"


@mcp.tool()
async def update_task_status(task_title_or_id: str, new_status: str) -> str:
    """Update task status: todo/in_progress/blocked/review/done/cancelled"""
    user = await _authenticate()
    if not user:
        return _auth_error()

    valid = {"todo", "in_progress", "blocked", "review", "done", "cancelled"}
    if new_status not in valid:
        return f"❌ Use: {', '.join(valid)}"

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
async def get_project_summary(project_name: str) -> str:
    """Full summary of a project — tasks, progress, blockers."""
    user = await _authenticate()
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

    lines = [f"**{proj.title}**",
             f"Status: {proj.status.value} | Priority: {proj.priority.value} | {proj.progress_pct}% done",
             f"Owner: {proj.owner.name if proj.owner else 'None'} | Due: {proj.due_date or 'not set'}",
             f"Tasks: {len(done_tasks)}/{len(tasks)} done | {len(overdue)} overdue"]
    if proj.blockers:
        lines.append(f"\n⚠️ BLOCKERS: {proj.blockers}")
    if open_tasks:
        lines.append("\nOpen tasks:")
        for t in open_tasks[:10]:
            who = t.assignee.name.split()[0] if t.assignee else "?"
            due = f" due {t.due_date}" if t.due_date else ""
            lines.append(f"  • [{t.priority.value}] {t.title} ({who}{due})")
    return "\n".join(lines)


@mcp.tool()
async def log_transcript_search(
    searched_for: str, got_back: str, was_correct: bool,
    note: Optional[str] = None, attendees: Optional[str] = None, meeting_date: Optional[str] = None,
) -> str:
    """Log whether Graph returned the right transcript. Call after every M365 transcript fetch."""
    user = await _authenticate()
    async with AsyncSessionLocal() as db:
        log = TranscriptSearchLog(
            user_id=user.id if user else None,
            search_query=searched_for, returned_title=got_back, returned_date=meeting_date,
            returned_attendees=[a.strip() for a in (attendees or "").split(",") if a.strip()],
            source="mcp", was_correct=was_correct, correction_note=note,
        )
        db.add(log)
        await db.commit()
    status = "correct" if was_correct else "WRONG"
    return f"Logged [{status}]: '{searched_for}' → '{got_back}'" + (f" — {note}" if not was_correct and note else "")


@mcp.tool()
async def get_transcript_diagnostics() -> str:
    """Accuracy report for transcript searches — find patterns in Graph API errors."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TranscriptSearchLog).order_by(TranscriptSearchLog.created_at.desc()).limit(50)
        )
        logs = result.scalars().all()
    total = len(logs)
    correct = sum(1 for l in logs if l.was_correct is True)
    wrong = sum(1 for l in logs if l.was_correct is False)
    acc = round((correct / max(correct + wrong, 1)) * 100)
    lines = [f"**Transcript Diagnostics** ({total} total) | Accuracy: {acc}% | Wrong: {wrong}", ""]
    for l in [l for l in logs if l.was_correct is False]:
        lines.append(f"  • '{l.search_query}' → '{l.returned_title}'" + (f"\n    {l.correction_note}" if l.correction_note else ""))
    return "\n".join(lines) if lines else "No data yet."
