"""
PulseOps MCP Server
Gives Claude direct access to the PulseOps FastAPI backend.
"""

import asyncio
import json
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# ---------------------------------------------------------------------------
# Load env
# ---------------------------------------------------------------------------
load_dotenv()

API_URL = os.getenv("PULSEOPS_API_URL", "http://localhost:8001/api/v1").rstrip("/")
API_KEY = os.getenv("PULSEOPS_API_KEY", "").strip()

# ---------------------------------------------------------------------------
# Auth: long-lived per-user API key (grab it from PulseOps Settings -> MCP
# Token). Sent as a bearer token on every request. Connect once — it never
# expires, so there is no login step and no 401-refresh dance.
# ---------------------------------------------------------------------------


async def _request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> Any:
    """Make an authenticated request using the long-lived API key."""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            f"{API_URL}{path}",
            headers=headers,
            params=params,
            json=json_body,
            timeout=30,
        )
        return resp


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
STATUS_EMOJI = {
    "in_progress": "🟢",
    "blocked": "🔴",
    "done": "✅",
    "completed": "✅",
    "todo": "📋",
    "planning": "📝",
    "on_hold": "⏸",
    "cancelled": "❌",
    "review": "🔍",
}

PRIORITY_EMOJI = {
    "critical": "🚨",
    "high": "🔺",
    "medium": "🟡",
    "low": "🔽",
}


def _se(status: str) -> str:
    return STATUS_EMOJI.get((status or "").lower(), "⬜")


def _pe(priority: str) -> str:
    return PRIORITY_EMOJI.get((priority or "").lower(), "")


def _fmt_project(p: dict) -> str:
    status = p.get("status", "unknown")
    priority = p.get("priority", "")
    due = p.get("due_date", "") or ""
    progress = p.get("progress_pct")
    line = f"  {_se(status)} [{status}] {p.get('title', '(untitled)')} {_pe(priority)}"
    if priority:
        line += f" | priority: {priority}"
    if due:
        line += f" | due: {due[:10]}"
    if progress is not None:
        line += f" | progress: {progress}%"
    return line


def _fmt_task(t: dict) -> str:
    done = "✅" if t.get("is_completed") else "⬜"
    priority = t.get("priority", "")
    due = t.get("due_date", "") or ""
    line = f"    {done} {t.get('title', '(untitled)')}"
    if priority:
        line += f" [{_pe(priority)}{priority}]"
    if due:
        line += f" due: {due[:10]}"
    return line


def _error(msg: str, status_code: int | None = None) -> str:
    code_str = f" (HTTP {status_code})" if status_code else ""
    return f"ERROR{code_str}: {msg}"


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
server = Server("pulseops")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_projects",
            description="List all projects in PulseOps. Optionally filter by status or priority.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status (e.g. in_progress, blocked, done)"},
                    "priority": {"type": "string", "description": "Filter by priority (e.g. high, medium, low)"},
                    "q": {"type": "string", "description": "Search query to filter projects by name"},
                },
            },
        ),
        Tool(
            name="get_project",
            description="Get full details of a project including its tasks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The UUID of the project"},
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="create_project",
            description="Create a new project in PulseOps.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Project title"},
                    "description": {"type": "string", "description": "Project description"},
                    "priority": {"type": "string", "description": "Priority: critical, high, medium, low"},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "List of tags"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="update_project",
            description="Update a project's fields (status, priority, progress, blockers, next_action, etc).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The UUID of the project to update"},
                    "status": {"type": "string", "description": "New status"},
                    "priority": {"type": "string", "description": "New priority"},
                    "progress_pct": {"type": "number", "description": "Progress percentage (0–100)"},
                    "blockers": {"type": "string", "description": "Description of current blockers"},
                    "next_action": {"type": "string", "description": "Next action item"},
                    "latest_update": {"type": "string", "description": "Latest status update note"},
                },
                "required": ["project_id"],
            },
        ),
        Tool(
            name="create_task",
            description="Create a task under a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The UUID of the parent project"},
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "description": "Priority: critical, high, medium, low"},
                    "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                    "assigned_to": {"type": "string", "description": "Email or name of the assignee"},
                },
                "required": ["project_id", "title"],
            },
        ),
        Tool(
            name="update_task",
            description="Update a task (mark complete, change priority, set due date).",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The UUID of the task to update"},
                    "is_completed": {"type": "boolean", "description": "Mark the task as completed"},
                    "priority": {"type": "string", "description": "New priority"},
                    "status": {"type": "string", "description": "New status"},
                    "due_date": {"type": "string", "description": "New due date in YYYY-MM-DD format"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="move_project",
            description="Move a project to a different Kanban column (change its status).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The UUID of the project to move"},
                    "new_status": {"type": "string", "description": "Target column/status (e.g. in_progress, done, blocked)"},
                },
                "required": ["project_id", "new_status"],
            },
        ),
        Tool(
            name="get_dashboard",
            description="Get workspace dashboard stats: total projects, blocked, overdue, recent activity, high priority items.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="search_projects",
            description="Search projects and tasks by keyword.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="process_email",
            description="Extract tasks, people, and deadlines from an email. Returns structured action items.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body text"},
                    "sender": {"type": "string", "description": "Sender's name or email address"},
                },
                "required": ["body"],
            },
        ),
        Tool(
            name="analyze_transcript",
            description="Analyze a meeting transcript and extract action items, decisions, and blockers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Meeting title or topic"},
                    "transcript": {"type": "string", "description": "Full transcript text"},
                },
                "required": ["title", "transcript"],
            },
        ),
        Tool(
            name="list_transcripts",
            description="List stored meeting transcripts (newest first) with summaries, action items, decisions, and blockers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "number", "description": "Max number of transcripts to return (default 20)"},
                },
            },
        ),
        Tool(
            name="get_transcript",
            description="Get one meeting transcript by ID, including the full raw transcript text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transcript_id": {"type": "string", "description": "The UUID of the transcript"},
                },
                "required": ["transcript_id"],
            },
        ),
        Tool(
            name="ai_chat",
            description="Send a message to the PulseOps AI assistant. It can answer questions about projects or create things.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Your message or question"},
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="ai_intake",
            description="Convert a raw natural language request into a structured project card (does not create the project — returns a suggestion for human review).",
            inputSchema={
                "type": "object",
                "properties": {
                    "raw_input": {"type": "string", "description": "Natural language description of the project or task"},
                },
                "required": ["raw_input"],
            },
        ),
        Tool(
            name="get_gantt",
            description="Get Gantt chart data: all projects with their tasks and date ranges.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
    except httpx.HTTPStatusError as e:
        result = _error(str(e), e.response.status_code)
    except Exception as e:
        result = _error(str(e))
    return [TextContent(type="text", text=result)]


async def _dispatch(name: str, args: dict) -> str:
    if name == "list_projects":
        return await _list_projects(args)
    elif name == "get_project":
        return await _get_project(args)
    elif name == "create_project":
        return await _create_project(args)
    elif name == "update_project":
        return await _update_project(args)
    elif name == "create_task":
        return await _create_task(args)
    elif name == "update_task":
        return await _update_task(args)
    elif name == "move_project":
        return await _move_project(args)
    elif name == "get_dashboard":
        return await _get_dashboard(args)
    elif name == "search_projects":
        return await _search_projects(args)
    elif name == "process_email":
        return await _process_email(args)
    elif name == "analyze_transcript":
        return await _analyze_transcript(args)
    elif name == "list_transcripts":
        return await _list_transcripts(args)
    elif name == "get_transcript":
        return await _get_transcript(args)
    elif name == "ai_chat":
        return await _ai_chat(args)
    elif name == "ai_intake":
        return await _ai_intake(args)
    elif name == "get_gantt":
        return await _get_gantt(args)
    else:
        return _error(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _list_projects(args: dict) -> str:
    params = {}
    if args.get("status"):
        params["status"] = args["status"]
    if args.get("priority"):
        params["priority"] = args["priority"]
    if args.get("q"):
        params["q"] = args["q"]

    resp = await _request("GET", "/projects/", params=params or None)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    data = resp.json()
    projects = data if isinstance(data, list) else data.get("projects", data.get("items", []))

    if not projects:
        return "No projects found."

    lines = [f"Projects ({len(projects)} total):"]
    for p in projects:
        lines.append(_fmt_project(p))
        tasks = p.get("tasks", [])
        for t in tasks:
            lines.append(_fmt_task(t))
    return "\n".join(lines)


async def _get_project(args: dict) -> str:
    project_id = args["project_id"]
    resp = await _request("GET", f"/projects/{project_id}")
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    p = resp.json()
    lines = [
        f"Project: {p.get('title', '(untitled)')}",
        f"  ID:          {p.get('id', '')}",
        f"  Status:      {_se(p.get('status',''))} {p.get('status','')}",
        f"  Priority:    {_pe(p.get('priority',''))} {p.get('priority','')}",
        f"  Progress:    {p.get('progress_pct', 0)}%",
        f"  Due Date:    {(p.get('due_date') or '')[:10] or 'not set'}",
        f"  Description: {p.get('description') or '—'}",
    ]
    if p.get("blockers"):
        lines.append(f"  Blockers:    {p['blockers']}")
    if p.get("next_action"):
        lines.append(f"  Next Action: {p['next_action']}")
    if p.get("latest_update"):
        lines.append(f"  Latest Update: {p['latest_update']}")

    tags = p.get("tags", [])
    if tags:
        lines.append(f"  Tags:        {', '.join(tags)}")

    tasks = p.get("tasks", [])
    if tasks:
        lines.append(f"\n  Tasks ({len(tasks)}):")
        for t in tasks:
            lines.append(_fmt_task(t))
    else:
        lines.append("\n  No tasks yet.")

    return "\n".join(lines)


async def _create_project(args: dict) -> str:
    body = {"title": args["title"]}
    for field in ("description", "priority", "due_date", "tags"):
        if args.get(field) is not None:
            body[field] = args[field]

    resp = await _request("POST", "/projects/", json_body=body)
    if resp.status_code not in (200, 201):
        return _error(resp.text, resp.status_code)

    p = resp.json()
    return (
        f"Project created successfully!\n"
        f"  ID:       {p.get('id', '')}\n"
        f"  Title:    {p.get('title', '')}\n"
        f"  Status:   {p.get('status', '')}\n"
        f"  Priority: {p.get('priority', '')}\n"
        f"  Due Date: {(p.get('due_date') or '')[:10] or 'not set'}"
    )


async def _update_project(args: dict) -> str:
    project_id = args.pop("project_id")
    body = {k: v for k, v in args.items() if v is not None}
    if not body:
        return "No fields to update provided."

    resp = await _request("PATCH", f"/projects/{project_id}", json_body=body)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    p = resp.json()
    lines = [f"Project updated: {p.get('title', project_id)}"]
    for k, v in body.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


async def _create_task(args: dict) -> str:
    body = {
        "project_id": args["project_id"],
        "title": args["title"],
    }
    for field in ("description", "priority", "due_date", "assigned_to"):
        if args.get(field) is not None:
            body[field] = args[field]

    resp = await _request("POST", "/tasks/", json_body=body)
    if resp.status_code not in (200, 201):
        return _error(resp.text, resp.status_code)

    t = resp.json()
    return (
        f"Task created successfully!\n"
        f"  ID:         {t.get('id', '')}\n"
        f"  Title:      {t.get('title', '')}\n"
        f"  Project ID: {t.get('project_id', '')}\n"
        f"  Priority:   {t.get('priority', '')}\n"
        f"  Due Date:   {(t.get('due_date') or '')[:10] or 'not set'}"
    )


async def _update_task(args: dict) -> str:
    task_id = args.pop("task_id")
    body = {k: v for k, v in args.items() if v is not None}
    if not body:
        return "No fields to update provided."

    resp = await _request("PATCH", f"/tasks/{task_id}", json_body=body)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    t = resp.json()
    done_str = "✅ Completed" if t.get("is_completed") else "⬜ In Progress"
    return (
        f"Task updated: {t.get('title', task_id)}\n"
        f"  Status: {done_str}\n"
        f"  Priority: {t.get('priority', '')}"
    )


async def _move_project(args: dict) -> str:
    body = {
        "project_id": args["project_id"],
        "new_status": args["new_status"],
    }
    resp = await _request("PATCH", "/kanban/move", json_body=body)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    data = resp.json()
    p = data if isinstance(data, dict) else {}
    return (
        f"Project moved to '{args['new_status']}' {_se(args['new_status'])}\n"
        f"  Project: {p.get('title', args['project_id'])}"
    )


async def _get_dashboard(args: dict) -> str:
    resp = await _request("GET", "/analytics/dashboard")
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    d = resp.json()
    lines = ["PulseOps Dashboard"]
    lines.append("=" * 40)

    # Try to handle various response shapes
    def _val(key: str, fallback: str = "N/A") -> str:
        return str(d.get(key, fallback))

    lines += [
        f"  Total Projects:    {_val('total_projects')}",
        f"  In Progress:       {_val('in_progress')}",
        f"  Blocked:           {_val('blocked')} 🔴",
        f"  Completed:         {_val('completed')}",
        f"  Overdue:           {_val('overdue')} ⚠️",
        f"  High Priority:     {_val('high_priority')}",
        f"  Total Tasks:       {_val('total_tasks')}",
        f"  Tasks Completed:   {_val('tasks_completed')}",
    ]

    recent = d.get("recent_activity", [])
    if recent:
        lines.append("\nRecent Activity:")
        for item in recent[:5]:
            if isinstance(item, dict):
                lines.append(f"  • {item.get('description', item.get('message', str(item)))}")
            else:
                lines.append(f"  • {item}")

    high_priority = d.get("high_priority_items", [])
    if high_priority:
        lines.append("\nHigh Priority Items:")
        for item in high_priority[:5]:
            if isinstance(item, dict):
                lines.append(f"  🔺 {item.get('title', str(item))}")
            else:
                lines.append(f"  🔺 {item}")

    return "\n".join(lines)


async def _search_projects(args: dict) -> str:
    query = args["query"]
    resp = await _request("GET", "/search/keyword", params={"q": query})
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    data = resp.json()
    projects = data.get("projects", []) if isinstance(data, dict) else data
    tasks = data.get("tasks", []) if isinstance(data, dict) else []

    if not projects and not tasks:
        return f"No results found for '{query}'."

    lines = [f"Search results for '{query}':"]
    if projects:
        lines.append(f"\nProjects ({len(projects)}):")
        for p in projects:
            lines.append(_fmt_project(p))
    if tasks:
        lines.append(f"\nTasks ({len(tasks)}):")
        for t in tasks:
            lines.append(_fmt_task(t))

    return "\n".join(lines)


async def _process_email(args: dict) -> str:
    body = {"body": args["body"]}
    if args.get("subject"):
        body["subject"] = args["subject"]
    if args.get("sender"):
        body["sender"] = args["sender"]

    resp = await _request("POST", "/ai/extract-email", json_body=body)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    data = resp.json()
    lines = ["Email Analysis Results:"]
    lines.append("=" * 40)

    action_items = data.get("action_items", data.get("tasks", []))
    if action_items:
        lines.append(f"\nAction Items ({len(action_items)}):")
        for item in action_items:
            if isinstance(item, dict):
                title = item.get("title", item.get("task", str(item)))
                assignee = item.get("assigned_to", item.get("assignee", ""))
                due = item.get("due_date", "")
                line = f"  • {title}"
                if assignee:
                    line += f" → {assignee}"
                if due:
                    line += f" (due: {due[:10]})"
                lines.append(line)
            else:
                lines.append(f"  • {item}")

    people = data.get("people", [])
    if people:
        lines.append(f"\nPeople Mentioned: {', '.join(str(p) for p in people)}")

    deadlines = data.get("deadlines", [])
    if deadlines:
        lines.append("\nDeadlines:")
        for d in deadlines:
            lines.append(f"  📅 {d}")

    summary = data.get("summary", data.get("reply", ""))
    if summary:
        lines.append(f"\nSummary:\n  {summary}")

    return "\n".join(lines)


async def _analyze_transcript(args: dict) -> str:
    body = {"title": args["title"], "transcript": args["transcript"]}

    resp = await _request("POST", "/ai/extract-transcript", json_body=body)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    data = resp.json()
    lines = [f"Transcript Analysis: {args['title']}"]
    lines.append("=" * 40)

    action_items = data.get("action_items", data.get("tasks", []))
    if action_items:
        lines.append(f"\nAction Items ({len(action_items)}):")
        for item in action_items:
            if isinstance(item, dict):
                title = item.get("title", item.get("task", str(item)))
                assignee = item.get("assigned_to", item.get("owner", ""))
                due = item.get("due_date", "")
                line = f"  ✅ {title}"
                if assignee:
                    line += f" → {assignee}"
                if due:
                    line += f" (due: {due[:10]})"
                lines.append(line)
            else:
                lines.append(f"  ✅ {item}")

    decisions = data.get("decisions", [])
    if decisions:
        lines.append("\nDecisions Made:")
        for d in decisions:
            lines.append(f"  🎯 {d}")

    blockers = data.get("blockers", [])
    if blockers:
        lines.append("\nBlockers Identified:")
        for b in blockers:
            lines.append(f"  🔴 {b}")

    summary = data.get("summary", data.get("reply", ""))
    if summary:
        lines.append(f"\nSummary:\n  {summary}")

    return "\n".join(lines)


async def _list_transcripts(args: dict) -> str:
    params = {"limit": int(args.get("limit") or 20)}
    resp = await _request("GET", "/ai/transcripts", params=params)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    data = resp.json()
    transcripts = data.get("transcripts", [])
    if not transcripts:
        return "No meeting transcripts stored yet."

    lines = [f"Meeting Transcripts ({len(transcripts)}):", "=" * 40]
    for t in transcripts:
        lines.append(f"\n📄 {t['title']}  [{t['id']}]")
        if t.get("meeting_date"):
            lines.append(f"  Date: {t['meeting_date']} | Source: {t.get('source', 'manual')}")
        if t.get("attendees"):
            lines.append(f"  Attendees: {', '.join(t['attendees'])}")
        if t.get("summary"):
            lines.append(f"  Summary: {t['summary'][:300]}")
        items = t.get("action_items") or []
        if items:
            lines.append(f"  Action items ({len(items)}):")
            for item in items:
                if isinstance(item, dict):
                    title = item.get("task", item.get("title", str(item)))
                    owner = item.get("owner", item.get("assigned_to", ""))
                    lines.append(f"    • {title}" + (f" → {owner}" if owner else ""))
                else:
                    lines.append(f"    • {item}")
        lines.append(f"  Tasks created: {'yes' if t.get('tasks_created') else 'no'}")
    return "\n".join(lines)


async def _get_transcript(args: dict) -> str:
    resp = await _request("GET", f"/ai/transcripts/{args['transcript_id']}")
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    t = resp.json()
    lines = [f"Transcript: {t['title']}  [{t['id']}]", "=" * 40]
    if t.get("meeting_date"):
        lines.append(f"Date: {t['meeting_date']} | Source: {t.get('source', 'manual')}")
    if t.get("attendees"):
        lines.append(f"Attendees: {', '.join(t['attendees'])}")
    if t.get("summary"):
        lines.append(f"\nSummary:\n{t['summary']}")
    if t.get("decisions"):
        lines.append("\nDecisions:")
        lines.extend(f"  🎯 {d}" for d in t["decisions"])
    if t.get("blockers"):
        lines.append("\nBlockers:")
        lines.extend(f"  🔴 {b}" for b in t["blockers"])
    items = t.get("action_items") or []
    if items:
        lines.append(f"\nAction items ({len(items)}):")
        for item in items:
            if isinstance(item, dict):
                title = item.get("task", item.get("title", str(item)))
                owner = item.get("owner", item.get("assigned_to", ""))
                lines.append(f"  • {title}" + (f" → {owner}" if owner else ""))
            else:
                lines.append(f"  • {item}")
    lines.append(f"\nFull transcript:\n{t.get('raw_transcript', '')}")
    return "\n".join(lines)


async def _ai_chat(args: dict) -> str:
    body = {"message": args["message"]}
    resp = await _request("POST", "/ai/chat", json_body=body)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    data = resp.json()
    reply = (
        data.get("reply")
        or data.get("response")
        or data.get("message")
        or data.get("content")
        or json.dumps(data, indent=2)
    )
    return f"PulseOps AI:\n{reply}"


async def _ai_intake(args: dict) -> str:
    body = {"raw_input": args["raw_input"]}
    resp = await _request("POST", "/ai/intake", json_body=body)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    data = resp.json()
    lines = ["Structured Project Suggestion (not yet created):"]
    lines.append("=" * 40)

    suggestion = data.get("project", data.get("suggestion", data))
    if isinstance(suggestion, dict):
        for key, val in suggestion.items():
            if val:
                lines.append(f"  {key}: {val}")
    else:
        lines.append(str(suggestion))

    lines.append("\nReview this suggestion and use create_project to create it if it looks right.")
    return "\n".join(lines)


async def _get_gantt(args: dict) -> str:
    resp = await _request("GET", "/analytics/gantt")
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    data = resp.json()
    projects = data if isinstance(data, list) else data.get("projects", data.get("items", []))

    if not projects:
        return "No Gantt data available."

    lines = ["Gantt Chart Data:"]
    lines.append("=" * 40)

    for p in projects:
        start = (p.get("start_date") or p.get("created_at") or "")[:10]
        end = (p.get("due_date") or p.get("end_date") or "")[:10]
        status = p.get("status", "")
        lines.append(f"\n{_se(status)} {p.get('title', '(untitled)')}")
        lines.append(f"     {start or '?'} → {end or '?'}  | {status}")

        tasks = p.get("tasks", [])
        for t in tasks:
            t_start = (t.get("start_date") or t.get("created_at") or "")[:10]
            t_due = (t.get("due_date") or "")[:10]
            done = "✅" if t.get("is_completed") else "⬜"
            lines.append(f"     {done} {t.get('title', '(untitled)')}: {t_start or '?'} → {t_due or '?'}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main():
    if not API_KEY:
        print(
            "WARNING: PULSEOPS_API_KEY not set — every request will 401. "
            "Grab your key from PulseOps Settings -> MCP Token and set "
            "PULSEOPS_API_KEY in your .env or Claude settings.",
            file=sys.stderr,
        )
    print("PulseOps MCP server ready", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
