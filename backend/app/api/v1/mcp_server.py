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
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.models import (
    Project, Task, ProjectStatus, PriorityLevel, User, TranscriptSearchLog,
    ActivityLog,
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


# ═══════════════════════════════════════════════════════════════════════════════
# Board / project management tools (parity with the local stdio MCP server).
# These mirror the REST endpoints in projects.py / kanban.py / analytics.py so a
# single hosted connection can manage the whole board — not just "my" tasks.
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_date(s: Optional[str]):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


async def _resolve_project(db, ref: str) -> Optional[Project]:
    """Look up a project by UUID first, then by partial title match."""
    ref = (ref or "").strip()
    try:
        proj = (await db.execute(select(Project).where(Project.id == UUID(ref)))).scalar_one_or_none()
        if proj:
            return proj
    except ValueError:
        pass
    return (await db.execute(
        select(Project).where(Project.title.ilike(f"%{ref}%")).limit(1)
    )).scalar_one_or_none()


def _bust_kanban_cache() -> None:
    """Clear the projects.py kanban cache so mutations show up immediately."""
    try:
        from app.api.v1.projects import _kanban_cache
        _kanban_cache.clear()
    except Exception:
        pass


@mcp.tool()
async def list_all_projects(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100,
) -> str:
    """
    List ALL projects on the board (everyone's, not just yours).
    status: intake/todo/in_progress/blocked/review/done/potential/cancelled
    priority: low/medium/high/urgent
    query: keyword match on title/description
    """
    user = await _authenticate()
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        q = (
            select(Project)
            .options(selectinload(Project.owner))
            .order_by(Project.kanban_order, Project.updated_at.desc())
        )
        if status:
            try:
                q = q.where(Project.status == ProjectStatus(status))
            except ValueError:
                pass
        if priority:
            try:
                q = q.where(Project.priority == PriorityLevel(priority))
            except ValueError:
                pass
        if query:
            q = q.where(or_(Project.title.ilike(f"%{query}%"), Project.description.ilike(f"%{query}%")))
        q = q.limit(max(1, min(limit, 200)))
        projects = (await db.execute(q)).scalars().all()

    if not projects:
        return "No projects found."

    lines = [f"**All projects** ({len(projects)}):\n"]
    for p in projects:
        owner = p.owner.name.split()[0] if p.owner else "—"
        due = f" | due {p.due_date}" if p.due_date else ""
        lines.append(
            f"• [{p.status.value}] {p.title} [{p.priority.value}] — {p.progress_pct}% | {owner}{due}\n  id: {p.id}"
        )
    return "\n".join(lines)


@mcp.tool()
async def get_project(project_id_or_name: str) -> str:
    """Full details of one project (by UUID or partial name): tasks, progress, blockers, dates, tags."""
    user = await _authenticate()
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        stub = await _resolve_project(db, project_id_or_name)
        if not stub:
            return f"❌ No project matching '{project_id_or_name}'."
        proj = (await db.execute(
            select(Project)
            .options(selectinload(Project.tasks).selectinload(Task.assignee), selectinload(Project.owner))
            .where(Project.id == stub.id)
        )).scalar_one()

    tasks = proj.tasks or []
    done = [t for t in tasks if t.is_completed]
    lines = [
        f"**{proj.title}**  (id: {proj.id})",
        f"Status: {proj.status.value} | Priority: {proj.priority.value} | {proj.progress_pct}% done",
        f"Owner: {proj.owner.name if proj.owner else 'None'} | Due: {proj.due_date or 'not set'}",
        f"Tasks: {len(done)}/{len(tasks)} done",
    ]
    if proj.description:
        lines.append(f"\n{proj.description}")
    if proj.tags:
        lines.append(f"Tags: {', '.join(proj.tags)}")
    if proj.blockers:
        lines.append(f"⚠️ Blockers: {proj.blockers}")
    if proj.next_action:
        lines.append(f"➡️ Next: {proj.next_action}")
    open_tasks = [t for t in tasks if not t.is_completed and t.status.value != "cancelled"]
    if open_tasks:
        lines.append("\nOpen tasks:")
        for t in open_tasks[:20]:
            who = t.assignee.name.split()[0] if t.assignee else "?"
            tdue = f" due {t.due_date}" if t.due_date else ""
            lines.append(f"  • [{t.priority.value}] {t.title} ({who}{tdue})")
    return "\n".join(lines)


@mcp.tool()
async def create_project(
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    status: str = "intake",
    due_date: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """
    Create a new project. priority=low/medium/high/urgent.
    status=intake/todo/in_progress/blocked/review/done/potential. due_date=YYYY-MM-DD.
    tags=comma-separated. You become the owner.
    """
    user = await _authenticate()
    if not user:
        return _auth_error()
    if user.role.value == "viewer":
        return "❌ Your role (viewer) cannot create projects."

    try:
        pri = PriorityLevel(priority.lower())
    except ValueError:
        pri = PriorityLevel.medium
    try:
        st = ProjectStatus(status.lower())
    except ValueError:
        st = ProjectStatus.intake
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    async with AsyncSessionLocal() as db:
        proj = Project(
            title=title, description=description, priority=pri, status=st,
            due_date=_parse_date(due_date), tags=tag_list,
            owner_id=user.id, created_by=user.id,
        )
        db.add(proj)
        await db.flush()
        db.add(ActivityLog(entity_type="project", entity_id=proj.id, user_id=user.id, action="created"))
        await db.commit()
        pid, ptitle = proj.id, proj.title
    _bust_kanban_cache()
    return f"✅ Created project **{ptitle}** [{st.value}/{pri.value}] — id: {pid}"


@mcp.tool()
async def update_project(
    project_id_or_name: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    progress_pct: Optional[int] = None,
    due_date: Optional[str] = None,
    blockers: Optional[str] = None,
    next_action: Optional[str] = None,
    latest_update: Optional[str] = None,
) -> str:
    """Update a project's fields. Only the owner/creator (or an admin) may edit."""
    user = await _authenticate()
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        proj = await _resolve_project(db, project_id_or_name)
        if not proj:
            return f"❌ No project matching '{project_id_or_name}'."
        if not (proj.owner_id == user.id or proj.created_by == user.id or user.role.value == "admin"):
            return "❌ You can only edit projects you own or created."

        changes = []
        if status:
            try:
                old = proj.status.value
                proj.status = ProjectStatus(status)
                changes.append(f"status {old}→{status}")
            except ValueError:
                pass
        if priority:
            try:
                proj.priority = PriorityLevel(priority)
                changes.append(f"priority→{priority}")
            except ValueError:
                pass
        if progress_pct is not None:
            proj.progress_pct = max(0, min(100, int(progress_pct)))
            changes.append(f"progress→{proj.progress_pct}%")
        if due_date is not None:
            proj.due_date = _parse_date(due_date)
            changes.append(f"due→{proj.due_date}")
        if blockers is not None:
            proj.blockers = blockers
            changes.append("blockers")
        if next_action is not None:
            proj.next_action = next_action
            changes.append("next_action")
        if latest_update is not None:
            proj.latest_update = latest_update
            changes.append("update")

        if not changes:
            return "No changes specified."
        db.add(ActivityLog(entity_type="project", entity_id=proj.id, user_id=user.id, action="updated"))
        await db.commit()
        title = proj.title
    _bust_kanban_cache()
    return f"✅ Updated **{title}**: {', '.join(changes)}"


@mcp.tool()
async def move_project(project_id_or_name: str, new_status: str) -> str:
    """
    Move a project to a different Kanban column.
    new_status: intake/todo/in_progress/blocked/review/done/potential/cancelled
    """
    user = await _authenticate()
    if not user:
        return _auth_error()
    try:
        st = ProjectStatus(new_status)
    except ValueError:
        return f"❌ Invalid status. Use: {', '.join(s.value for s in ProjectStatus)}"

    async with AsyncSessionLocal() as db:
        proj = await _resolve_project(db, project_id_or_name)
        if not proj:
            return f"❌ No project matching '{project_id_or_name}'."
        old = proj.status.value
        proj.status = st
        db.add(ActivityLog(entity_type="project", entity_id=proj.id, user_id=user.id,
                           action="moved", old_value=old, new_value=st.value))
        await db.commit()
        title = proj.title
    _bust_kanban_cache()
    return f"✅ Moved **{title}**: {old} → {st.value}"


@mcp.tool()
async def get_dashboard() -> str:
    """Workspace dashboard: project counts by status, overdue, task totals, and top high-priority items."""
    user = await _authenticate()
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        async def _count(*where):
            stmt = select(func.count()).select_from(Project)
            for w in where:
                stmt = stmt.where(w)
            return (await db.execute(stmt)).scalar()

        total = await _count()
        active = await _count(Project.status.in_([ProjectStatus.in_progress, ProjectStatus.review]))
        blocked = await _count(Project.status == ProjectStatus.blocked)
        intake = await _count(Project.status == ProjectStatus.intake)
        done_total = await _count(Project.status == ProjectStatus.done)
        overdue = await _count(Project.due_date < date.today(), Project.status.notin_([ProjectStatus.done]))
        total_tasks = (await db.execute(select(func.count()).select_from(Task))).scalar()
        open_tasks = (await db.execute(
            select(func.count()).select_from(Task).where(Task.is_completed == False)
        )).scalar()
        hp = (await db.execute(
            select(Project)
            .where(Project.priority.in_([PriorityLevel.high, PriorityLevel.urgent]),
                   Project.status.notin_([ProjectStatus.done]))
            .order_by(Project.due_date)
            .limit(5)
        )).scalars().all()

    lines = [
        "**PulseOps Dashboard**",
        "=" * 32,
        f"Projects: {total} total | {active} active | {blocked} blocked 🔴 | {intake} intake | {done_total} done",
        f"Overdue: {overdue} ⚠️",
        f"Tasks: {total_tasks} total | {open_tasks} open",
    ]
    if hp:
        lines.append("\nHigh-priority (open):")
        for p in hp:
            due = f" (due {p.due_date})" if p.due_date else ""
            lines.append(f"  🔺 {p.title} [{p.priority.value}]{due}")
    return "\n".join(lines)


@mcp.tool()
async def get_gantt() -> str:
    """Timeline view: active projects with start (created) → due dates and their open tasks."""
    user = await _authenticate()
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        projects = (await db.execute(
            select(Project)
            .options(selectinload(Project.tasks))
            .where(Project.status.notin_([ProjectStatus.done, ProjectStatus.cancelled]))
            .order_by(Project.created_at)
        )).scalars().all()

    if not projects:
        return "No active projects for the timeline."

    lines = ["**Gantt / Timeline**", "=" * 32]
    for p in projects:
        start = p.created_at.date() if p.created_at else "?"
        end = p.due_date or "?"
        lines.append(f"\n[{p.status.value}] {p.title}: {start} → {end}")
        for t in (p.tasks or []):
            if t.is_completed:
                continue
            lines.append(f"   • {t.title} → {t.due_date or '?'}")
    return "\n".join(lines)


@mcp.tool()
async def search_projects(query: str) -> str:
    """Keyword search across all projects and tasks by title/description."""
    user = await _authenticate()
    if not user:
        return _auth_error()

    async with AsyncSessionLocal() as db:
        projs = (await db.execute(
            select(Project)
            .where(or_(Project.title.ilike(f"%{query}%"), Project.description.ilike(f"%{query}%")))
            .limit(20)
        )).scalars().all()
        tasks = (await db.execute(
            select(Task).options(selectinload(Task.project))
            .where(Task.title.ilike(f"%{query}%")).limit(20)
        )).scalars().all()

    if not projs and not tasks:
        return f"No results for '{query}'."
    lines = [f"**Search: '{query}'**"]
    if projs:
        lines.append(f"\nProjects ({len(projs)}):")
        for p in projs:
            lines.append(f"  • [{p.status.value}] {p.title} — id: {p.id}")
    if tasks:
        lines.append(f"\nTasks ({len(tasks)}):")
        for t in tasks:
            pj = t.project.title if t.project else "?"
            lines.append(f"  • {t.title} ({pj})")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# AI-backed tools — thin wrappers that reuse the REST handlers in ai.py so all
# LLM/dedup/persistence logic stays in one place. Results are returned as JSON.
# ═══════════════════════════════════════════════════════════════════════════════

def _as_json(obj) -> str:
    import json
    payload = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj
    return "```json\n" + json.dumps(payload, indent=2, default=str) + "\n```"


@mcp.tool()
async def ai_chat(message: str) -> str:
    """Ask the PulseOps AI assistant a question about your projects, or tell it to take an action."""
    user = await _authenticate()
    if not user:
        return _auth_error()
    from app.api.v1.ai import ai_chat as _handler, _ChatRequest
    async with AsyncSessionLocal() as db:
        result = await _handler(_ChatRequest(message=message), db=db, current_user=user)
    if isinstance(result, dict):
        import json
        return result.get("reply") or result.get("message") or json.dumps(result, indent=2, default=str)
    return str(result)


@mcp.tool()
async def process_email(body: str, subject: Optional[str] = None, sender: Optional[str] = None) -> str:
    """Extract action items, people, and deadlines from an email (creates an email-ingestion record)."""
    user = await _authenticate()
    if not user:
        return _auth_error()
    from starlette.background import BackgroundTasks
    from app.api.v1.ai import extract_email as _handler
    from app.schemas.schemas import EmailAnalysisRequest
    async with AsyncSessionLocal() as db:
        out = await _handler(
            EmailAnalysisRequest(subject=subject, body=body, sender=sender),
            background_tasks=BackgroundTasks(), db=db, current_user=user,
        )
    return _as_json(out)


@mcp.tool()
async def analyze_transcript(
    title: str, transcript: str, meeting_date: Optional[str] = None, source: str = "mcp",
) -> str:
    """Analyze a meeting transcript and extract action items, decisions, and blockers."""
    user = await _authenticate()
    if not user:
        return _auth_error()
    from starlette.background import BackgroundTasks
    from app.api.v1.ai import extract_transcript as _handler
    from app.schemas.schemas import TranscriptAnalysisRequest
    async with AsyncSessionLocal() as db:
        out = await _handler(
            TranscriptAnalysisRequest(
                title=title, raw_transcript=transcript, source=source,
                meeting_date=_parse_date(meeting_date),
            ),
            background_tasks=BackgroundTasks(), db=db, current_user=user,
        )
    return _as_json(out)


@mcp.tool()
async def ai_intake(raw_input: str) -> str:
    """Turn a raw natural-language request into a structured project card (for review — priority is a suggestion)."""
    user = await _authenticate()
    if not user:
        return _auth_error()
    from starlette.background import BackgroundTasks
    from app.api.v1.ai import process_intake as _handler
    from app.schemas.schemas import IntakeRequest
    async with AsyncSessionLocal() as db:
        out = await _handler(
            IntakeRequest(raw_input=raw_input),
            background_tasks=BackgroundTasks(), db=db, current_user=user,
        )
    return _as_json(out)
