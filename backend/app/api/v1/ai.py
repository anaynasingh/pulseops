"""
PulseOps — AI API Endpoints
All AI-powered analysis, extraction, and generation endpoints.
"""
from datetime import date, timedelta
from uuid import UUID
from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.models import (
    Project, Task, AIInsight, AISummary, RequestIntake, MeetingTranscript,
    EmailIngestion, ProjectHealth, User, IntakeStatus, TranscriptSearchLog
)
import logging
logger = logging.getLogger(__name__)
from app.schemas.schemas import (
    IntakeRequest, IntakeResult, IntakeOut, IntakeConfirmRequest, ConfirmIntakeResult,
    EmailAnalysisRequest, EmailAnalysisResult, EmailIngestionOut,
    TranscriptAnalysisRequest, TranscriptAnalysisResult, TranscriptOut,
    SummaryRequest, SummaryOut,
    PrioritySuggestionRequest, PrioritySuggestionOut,
    ProjectOut, AIInsightOut, TaskOut,
    PriorityLevel, ProjectStatus
)
from app.core.deps import get_current_user, require_writer
from app.api.v1.projects import _log_activity as _log_project_activity, _can_edit_project, _kanban_cache
from app.api.v1.tasks import _log_activity as _log_task_activity
from app.services.ai_service import (
    structured_completion, chat_completion,
    INTAKE_SYSTEM, EMAIL_SYSTEM, TRANSCRIPT_SYSTEM,
    PRIORITY_SYSTEM, HEALTH_SYSTEM, SUMMARY_SYSTEM,
)
from app.services.embedding import embed_and_store, embed_and_store_bg
from app.services.user_service import find_or_create_user_by_name
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/ai", tags=["ai"])


# ── Internal Pydantic models for structured AI outputs ────────────────────────

class _IntakeAIOutput(BaseModel):
    title: str
    description: str
    project_type: str
    # AI classification: "project" or "task". Default covers omitted; validator coerces bad provided values.
    suggested_item_type: Literal["project", "task"] = "project"
    suggested_tags: List[str]
    suggested_subtasks: List[str]
    suggested_next_steps: List[str]
    suggested_due_date: Optional[str] = None
    suggested_priority: str   # low/medium/high/urgent
    suggested_owners: List[str]
    suggested_stakeholders: List[str]
    ai_reasoning: str

    @field_validator("suggested_item_type", mode="before")
    @classmethod
    def _coerce_item_type(cls, v):
        # Coerce any unknown/blank value the model emits to the safe default "project".
        # (Missing values fall back to the field default and never reach this validator.)
        if isinstance(v, str) and v.strip().lower() in ("project", "task"):
            return v.strip().lower()
        return "project"


class _EmailAIOutput(BaseModel):
    summary: str
    extracted_tasks: List[dict]
    extracted_people: List[str]
    extracted_deadlines: List[dict]
    extracted_blockers: List[str]


class _TranscriptAIOutput(BaseModel):
    summary: str
    action_items: List[dict]
    decisions: List[str]
    blockers: List[str]
    attendees: List[str]


class _PriorityAIOutput(BaseModel):
    suggested_priority: str
    reasoning: str
    factors: List[str]


class _HealthAIOutput(BaseModel):
    health_status: str
    health_score: int
    risk_score: int
    delivery_confidence: int
    reasoning: str


class _MultiTaskOutput(BaseModel):
    tasks: List[dict]   # [{title, description, priority, assignee_name, due_date_offset_days}]


# ── Request bodies ─────────────────────────────────────────────────────────────

class _TranscriptCreateTasksRequest(BaseModel):
    selected_indices: List[int]
    project_id: UUID


class _ConfirmTasksRequest(BaseModel):
    tasks: List[dict]
    project_id: Optional[str] = None


# ── AI Request Intake ─────────────────────────────────────────────────────────

@router.post("/intake", response_model=IntakeOut, status_code=201)
async def process_intake(
    payload: IntakeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process a raw natural-language request.
    Returns structured project metadata for human review.
    Priority is ALWAYS a suggestion — never auto-confirmed.
    """
    today = date.today().isoformat()
    user_prompt = f"""
Today's date: {today}

Raw request:
\"\"\"{payload.raw_input}\"\"\"

Generate structured project information from this request.
"""
    ai_output: _IntakeAIOutput = await structured_completion(
        system_prompt=INTAKE_SYSTEM,
        user_prompt=user_prompt,
        response_model=_IntakeAIOutput,
        temperature=0.3,
    )

    # Parse due date safely
    due_date = None
    if ai_output.suggested_due_date:
        try:
            due_date = date.fromisoformat(ai_output.suggested_due_date)
        except ValueError:
            due_date = date.today() + timedelta(days=30)

    intake = RequestIntake(
        raw_input=payload.raw_input,
        generated_title=ai_output.title,
        generated_description=ai_output.description,
        project_type=ai_output.project_type,
        suggested_item_type=ai_output.suggested_item_type,
        suggested_tags=ai_output.suggested_tags,
        suggested_subtasks=ai_output.suggested_subtasks,
        suggested_next_steps=ai_output.suggested_next_steps,
        suggested_due_date=due_date,
        suggested_priority=PriorityLevel(ai_output.suggested_priority),
        suggested_owners=ai_output.suggested_owners,
        ai_reasoning=ai_output.ai_reasoning,
        submitted_by=current_user.id,
        intake_status=IntakeStatus.pending,
    )
    db.add(intake)
    await db.commit()
    await db.refresh(intake)

    # Embed in background (use session-safe version — request session is closed by then)
    background_tasks.add_task(
        embed_and_store_bg, "project",
        intake.id,
        f"{ai_output.title} {ai_output.description}",
        {"intake_id": str(intake.id), "title": ai_output.title},
    )

    return IntakeOut.model_validate(intake)


@router.post("/intake/{intake_id}/confirm", response_model=ConfirmIntakeResult, status_code=201)
async def confirm_intake(
    intake_id: UUID,
    payload: IntakeConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_writer),
):
    """
    Human confirms (or adjusts) the AI-suggested intake and creates real work items.

    The intake is classified as a project or a task (Option C). The confirm routes to:
      - a new project (+ its suggested subtasks as Task rows), or
      - one or more tasks added to an existing project (with edit-permission check), or
      - one or more tasks added to a freshly-created parent project.
    The confirmed_priority field is REQUIRED — ensuring human sign-off.
    """
    from datetime import datetime as dt
    try:
        # Atomically claim the intake: FOR UPDATE serializes concurrent confirms for the
        # same intake_id. The first request holds the row lock until commit; a second
        # concurrent request blocks, then re-reads intake_status=confirmed and 409s —
        # preventing duplicate project/task fanout (TOCTOU race).
        intake_res = await db.execute(
            select(RequestIntake).where(RequestIntake.id == intake_id).with_for_update()
        )
        intake = intake_res.scalar_one_or_none()
        if not intake:
            raise HTTPException(status_code=404, detail="Intake not found")
        if intake.intake_status != IntakeStatus.pending:
            raise HTTPException(status_code=409, detail="Intake already processed")

        # Resolve item type: request override wins; else intake's AI classification;
        # null/legacy rows (created before the column existed) default to "project".
        intake_type = intake.suggested_item_type if intake.suggested_item_type in ("project", "task") else "project"
        resolved_type = payload.item_type or intake_type

        # Default owner/assignee to the confirming user "unless otherwise specified".
        # model_fields_set distinguishes an omitted field (=> default to current_user)
        # from an explicit null (=> caller intends ownerless/unassigned, respected).
        # A concrete UUID is used as-is. Applied to new projects (Routes 1 + 3) and to
        # every task created here; an existing project's owner (Route 2) is never touched.
        resolved_owner_id = (
            payload.owner_id if "owner_id" in payload.model_fields_set else current_user.id
        )
        resolved_assignee_id = (
            payload.assigned_to if "assigned_to" in payload.model_fields_set else current_user.id
        )

        # Clean subtask titles (JSONB list — guard against non-strings/blanks).
        subtask_titles = [s.strip() for s in (intake.suggested_subtasks or []) if isinstance(s, str) and s.strip()]

        created_tasks: List[Task] = []

        if resolved_type == "project":
            # ── Route 1: new project + its subtasks as Task rows ──
            project = Project(
                title=payload.title or intake.generated_title or "Untitled Project",
                description=payload.description or intake.generated_description,
                status=ProjectStatus.intake,
                priority=payload.confirmed_priority,  # ← Human-confirmed priority
                owner_id=resolved_owner_id,  # confirming user unless owner_id explicitly given
                team_id=payload.team_id,
                tags=intake.suggested_tags or [],
                due_date=intake.suggested_due_date,
                next_action=(intake.suggested_next_steps or [])[0] if intake.suggested_next_steps else None,
                created_by=current_user.id,
            )
            db.add(project)
            await db.flush()
            await _log_project_activity(db, project.id, current_user.id, "created")
            task_titles = subtask_titles  # may be empty → zero tasks
        else:
            # ── Route 2/3: task(s) under an existing or new parent project ──
            if payload.target_project_id is not None:
                # Route 2: existing project — must exist and be editable by this user.
                proj_res = await db.execute(select(Project).where(Project.id == payload.target_project_id))
                project = proj_res.scalar_one_or_none()
                if not project:
                    raise HTTPException(status_code=404, detail="Target project not found")
                if not _can_edit_project(project, current_user):
                    raise HTTPException(status_code=403, detail="You do not have permission to add tasks to this project")
            else:
                # Route 3: new minimal parent project (override survival per plan).
                project = Project(
                    title=payload.new_project_title or intake.generated_title or "Untitled Project",
                    description=payload.description or intake.generated_description,
                    status=ProjectStatus.intake,
                    priority=payload.confirmed_priority,
                    owner_id=resolved_owner_id,  # confirming user unless owner_id explicitly given
                    team_id=payload.team_id,
                    tags=intake.suggested_tags or [],
                    due_date=intake.suggested_due_date,
                    next_action=(intake.suggested_next_steps or [])[0] if intake.suggested_next_steps else None,
                    created_by=current_user.id,
                )
                db.add(project)
                await db.flush()
                await _log_project_activity(db, project.id, current_user.id, "created")
            # A task intake with no subtasks becomes a single task from the generated title.
            task_titles = subtask_titles or [intake.generated_title or "Untitled Task"]

        for title in task_titles:
            t = Task(
                project_id=project.id,
                title=title,
                status=ProjectStatus.todo,
                priority=payload.confirmed_priority,
                assigned_to=resolved_assignee_id,  # confirming user unless assigned_to explicitly given
                created_by=current_user.id,
            )
            db.add(t)
            created_tasks.append(t)

        if created_tasks:
            await db.flush()  # populate task ids before logging
            for t in created_tasks:
                await _log_task_activity(db, t.id, current_user.id, "task_created", t.title)

        intake.intake_status = IntakeStatus.confirmed
        intake.user_confirmed_priority = payload.confirmed_priority
        intake.project_id = project.id
        intake.confirmed_by = current_user.id
        intake.confirmed_at = dt.utcnow()

        await db.commit()

        # Reload the parent project with all relationships needed to serialize ProjectOut.
        proj_res = await db.execute(
            select(Project)
            .options(
                selectinload(Project.owner),
                selectinload(Project.tasks).selectinload(Task.assignee),
                selectinload(Project.insights),
                selectinload(Project.health_records),
            )
            .where(Project.id == project.id)
        )
        project_out = ProjectOut.model_validate(proj_res.scalar_one())

        # Reload created tasks WITH relationships — TaskOut carries assignee + project,
        # so avoid lazy-load during async serialization (H3).
        tasks_out: List[TaskOut] = []
        task_ids = [t.id for t in created_tasks]
        if task_ids:
            tres = await db.execute(
                select(Task)
                .options(selectinload(Task.assignee), selectinload(Task.project))
                .where(Task.id.in_(task_ids))
            )
            tasks_out = [TaskOut.model_validate(t) for t in tres.scalars().all()]

        # Bust the kanban server-side cache so the new project/tasks surface immediately.
        _kanban_cache.clear()

        return ConfirmIntakeResult(
            item_type=resolved_type,
            project=project_out,
            tasks_created=len(tasks_out),
            tasks=tasks_out,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"confirm_intake failed for {intake_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to confirm intake: {str(exc)}")


# ── Email Intelligence ────────────────────────────────────────────────────────

@router.post("/extract-email", response_model=EmailIngestionOut, status_code=201)
async def extract_email(
    payload: EmailAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_prompt = f"""
Subject: {payload.subject or 'N/A'}
From: {payload.sender or 'N/A'}
To: {', '.join(payload.recipients) or 'N/A'}

Email body:
\"\"\"{payload.body}\"\"\"
"""
    ai_output: _EmailAIOutput = await structured_completion(
        system_prompt=EMAIL_SYSTEM,
        user_prompt=user_prompt,
        response_model=_EmailAIOutput,
    )

    record = EmailIngestion(
        subject=payload.subject,
        raw_body=payload.body,
        sender=payload.sender,
        recipients=payload.recipients,
        summary=ai_output.summary,
        extracted_tasks=ai_output.extracted_tasks,
        extracted_people=ai_output.extracted_people,
        extracted_deadlines=ai_output.extracted_deadlines,
        extracted_blockers=ai_output.extracted_blockers,
        processed_by=current_user.id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    background_tasks.add_task(
        embed_and_store_bg, "email", record.id,
        f"{payload.subject or ''} {payload.body[:1000]}",
        {"email_id": str(record.id)},
    )

    return EmailIngestionOut.model_validate(record)


# ── Meeting Transcript Analysis ───────────────────────────────────────────────

@router.post("/extract-transcript", response_model=TranscriptOut, status_code=201)
async def extract_transcript(
    payload: TranscriptAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_prompt = f"""
Meeting title: {payload.title}
Date: {payload.meeting_date or 'Unknown'}
Source: {payload.source}

Transcript:
\"\"\"{payload.raw_transcript}\"\"\"
"""
    ai_output: _TranscriptAIOutput = await structured_completion(
        system_prompt=TRANSCRIPT_SYSTEM,
        user_prompt=user_prompt,
        response_model=_TranscriptAIOutput,
    )

    record = MeetingTranscript(
        project_id=payload.project_id,
        title=payload.title,
        raw_transcript=payload.raw_transcript,
        source=payload.source,
        summary=ai_output.summary,
        action_items=ai_output.action_items,
        decisions=ai_output.decisions,
        blockers=ai_output.blockers,
        attendees=ai_output.attendees,
        meeting_date=payload.meeting_date,
        uploaded_by=current_user.id,
    )
    db.add(record)

    # Auto-log every transcript analysis for Graph API diagnostics
    search_log = TranscriptSearchLog(
        user_id=current_user.id,
        search_query=payload.title,
        returned_title=payload.title,
        returned_date=str(payload.meeting_date) if payload.meeting_date else None,
        returned_attendees=ai_output.attendees or [],
        source=payload.source,
        was_correct=None,  # user feedback added later via /transcript-feedback
    )
    db.add(search_log)

    await db.commit()
    await db.refresh(record)
    await db.refresh(search_log)

    # Store search_log ID on the transcript so feedback can reference it
    record.meta_log_id = str(search_log.id) if hasattr(record, 'meta_log_id') else None

    background_tasks.add_task(
        embed_and_store_bg, "meeting", record.id,
        f"{payload.title} {payload.raw_transcript[:2000]}",
        {"meeting_id": str(record.id), "title": payload.title},
    )

    return TranscriptOut.model_validate(record)


class _TranscriptFeedbackRequest(BaseModel):
    log_id: UUID
    was_correct: bool
    correction_note: Optional[str] = None  # "wrong date", "pulled last week's meeting", etc.


@router.post("/transcript-feedback", response_model=dict)
async def transcript_feedback(
    payload: _TranscriptFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record whether the transcript search returned the right meeting.
    This builds a dataset for diagnosing Microsoft Graph search issues."""
    result = await db.execute(
        select(TranscriptSearchLog).where(TranscriptSearchLog.id == payload.log_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Log entry not found")

    log.was_correct = payload.was_correct
    log.correction_note = payload.correction_note
    await db.commit()

    return {
        "recorded": True,
        "log_id": str(log.id),
        "was_correct": log.was_correct,
        "message": "Thanks — this helps us find the pattern in Graph API errors." if not payload.was_correct else "Great, logged.",
    }


@router.get("/transcript-search-diagnostics", response_model=dict)
async def transcript_search_diagnostics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all transcript search logs for Claude to diagnose Graph API patterns."""
    result = await db.execute(
        select(TranscriptSearchLog)
        .order_by(TranscriptSearchLog.created_at.desc())
        .limit(100)
    )
    logs = result.scalars().all()

    total = len(logs)
    correct = sum(1 for l in logs if l.was_correct is True)
    wrong = sum(1 for l in logs if l.was_correct is False)
    unreviewed = sum(1 for l in logs if l.was_correct is None)

    wrong_logs = [
        {
            "id": str(l.id),
            "searched_for": l.search_query,
            "got_back": l.returned_title,
            "date_returned": l.returned_date,
            "source": l.source,
            "note": l.correction_note,
            "at": l.created_at.isoformat(),
        }
        for l in logs if l.was_correct is False
    ]

    return {
        "summary": {"total": total, "correct": correct, "wrong": wrong, "unreviewed": unreviewed},
        "accuracy_pct": round((correct / max(correct + wrong, 1)) * 100, 1),
        "wrong_cases": wrong_logs,
        "all_logs": [
            {
                "id": str(l.id),
                "query": l.search_query,
                "returned": l.returned_title,
                "source": l.source,
                "correct": l.was_correct,
                "at": l.created_at.isoformat(),
            }
            for l in logs
        ],
    }


@router.post("/transcript/{transcript_id}/create-tasks", response_model=dict, status_code=201)
async def create_tasks_from_transcript(
    transcript_id: UUID,
    payload: _TranscriptCreateTasksRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create tasks from selected action items in a meeting transcript."""
    result = await db.execute(
        select(MeetingTranscript).where(MeetingTranscript.id == transcript_id)
    )
    transcript = result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    action_items = transcript.action_items or []
    created_tasks = []

    for idx in payload.selected_indices:
        if idx < 0 or idx >= len(action_items):
            continue
        item = action_items[idx]

        # Resolve assignee
        assignee_user = None
        if item.get("owner"):
            assignee_user = await find_or_create_user_by_name(db, item["owner"])

        # Parse deadline
        due_date = None
        if item.get("deadline"):
            try:
                due_date = date.fromisoformat(item["deadline"])
            except (ValueError, TypeError):
                due_date = date.today() + timedelta(days=14)

        # Validate priority
        raw_priority = item.get("priority", "medium")
        if raw_priority not in ("low", "medium", "high", "urgent"):
            raw_priority = "medium"

        task = Task(
            project_id=payload.project_id,
            title=item.get("task", "Untitled task"),
            description=f"From meeting: {transcript.title}. Owner: {item.get('owner', 'TBD')}. Deadline: {item.get('deadline', 'TBD')}",
            priority=PriorityLevel(raw_priority),
            status=ProjectStatus.todo,
            # No task is left unassigned: fall back to the creator.
            assigned_to=assignee_user.id if assignee_user else current_user.id,
            due_date=due_date,
            created_by=current_user.id,
        )
        db.add(task)
        created_tasks.append(task)

    transcript.tasks_created = True
    await db.commit()

    # Reload tasks with assignees for serialization
    task_outs = []
    for t in created_tasks:
        await db.refresh(t)
        res = await db.execute(
            select(Task).options(selectinload(Task.assignee), selectinload(Task.project)).where(Task.id == t.id)
        )
        task_outs.append(TaskOut.model_validate(res.scalar_one()))

    return {"tasks_created": len(task_outs), "tasks": [t.model_dump(mode="json") for t in task_outs]}


# ── Meeting Transcript Reading (used by MCP / Claude bridge) ─────────────────

@router.get("/transcripts", response_model=dict)
async def list_transcripts(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List stored meeting transcripts (newest first) with summaries and action items."""
    result = await db.execute(
        select(MeetingTranscript)
        .order_by(MeetingTranscript.created_at.desc())
        .limit(min(limit, 100))
    )
    transcripts = result.scalars().all()
    return {
        "count": len(transcripts),
        "transcripts": [
            {
                "id": str(t.id),
                "title": t.title,
                "meeting_date": t.meeting_date.isoformat() if t.meeting_date else None,
                "source": t.source,
                "summary": t.summary,
                "action_items": t.action_items or [],
                "decisions": t.decisions or [],
                "blockers": t.blockers or [],
                "attendees": t.attendees or [],
                "tasks_created": t.tasks_created,
                "project_id": str(t.project_id) if t.project_id else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transcripts
        ],
    }


@router.get("/transcripts/{transcript_id}", response_model=dict)
async def get_transcript(
    transcript_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get one meeting transcript including its full raw text."""
    result = await db.execute(
        select(MeetingTranscript).where(MeetingTranscript.id == transcript_id)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return {
        "id": str(t.id),
        "title": t.title,
        "meeting_date": t.meeting_date.isoformat() if t.meeting_date else None,
        "source": t.source,
        "summary": t.summary,
        "action_items": t.action_items or [],
        "decisions": t.decisions or [],
        "blockers": t.blockers or [],
        "attendees": t.attendees or [],
        "tasks_created": t.tasks_created,
        "project_id": str(t.project_id) if t.project_id else None,
        "raw_transcript": t.raw_transcript,
    }


# ── Claude Code Bridge Chat ───────────────────────────────────────────────────

class _ClaudeChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # Claude Code session id for follow-up turns


@router.post("/claude-chat", response_model=dict)
async def claude_chat(
    payload: _ClaudeChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Forward a chat message to the Claude Code bridge, as THIS user.

    The bridge executes the query with Claude Code + the PulseOps MCP tools, so
    Claude can read transcripts, create tasks, move projects, etc. We forward the
    caller's OWN PulseOps key and (if connected) their OWN Microsoft token cache,
    so the assistant acts and reads as them — never as a shared account.
    """
    import os
    import base64
    import secrets
    import httpx
    from app.core.crypto import decrypt_str

    bridge_url = os.getenv("CLAUDE_BRIDGE_URL", "http://localhost:8765").rstrip("/")
    # Shared secret for a remote (Railway) bridge. Must match BRIDGE_SECRET on
    # the bridge service. Empty for a local bridge that runs without a secret.
    bridge_secret = os.getenv("BRIDGE_SECRET", "").strip()
    headers = {"X-Bridge-Secret": bridge_secret} if bridge_secret else {}

    # Per-user PulseOps identity: the assistant acts as this user (their own MCP key).
    if not current_user.api_key:
        current_user.api_key = secrets.token_urlsafe(32)
        await db.commit()
        await db.refresh(current_user)

    # Per-user Microsoft access: forward this user's own token cache if connected.
    # Absent → the bridge runs without M365 tools for this request; it must NEVER
    # fall back to another user's mailbox.
    m365_token_b64 = None
    if current_user.m365_token_cache:
        try:
            cache_json = decrypt_str(current_user.m365_token_cache)
            m365_token_b64 = base64.b64encode(cache_json.encode("utf-8")).decode("ascii")
        except Exception:
            logger.warning("Could not decrypt M365 token cache for user %s", current_user.id)
            m365_token_b64 = None

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=5.0)) as client:
            resp = await client.post(
                f"{bridge_url}/chat",
                json={
                    "message": payload.message,
                    "session_id": payload.session_id,
                    "user_email": current_user.email,
                    "pulseops_token": current_user.api_key,
                    "m365_token_b64": m365_token_b64,
                },
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise HTTPException(
            status_code=503,
            detail="Claude bridge is not running. Start it with: python claude-bridge/bridge.py",
        )
    except httpx.HTTPStatusError as exc:
        detail = "Claude bridge returned an error."
        try:
            detail = exc.response.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Claude took too long to respond. Try a simpler request.",
        )


# ── AI Summary Generation ─────────────────────────────────────────────────────

@router.post("/summarize", response_model=dict)
async def generate_summary(
    payload: SummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate daily/weekly/executive/blocker summary for the workspace or a specific project."""
    # Build context
    if payload.entity_id:
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.tasks), selectinload(Project.insights))
            .where(Project.id == payload.entity_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        context = f"""
Project: {project.title}
Status: {project.status}
Priority: {project.priority}
Progress: {project.progress_pct}%
Due date: {project.due_date}
Blockers: {project.blockers or 'None'}
Next action: {project.next_action or 'None'}
Latest update: {project.latest_update or 'None'}
Tasks: {len(project.tasks)} total
"""
    else:
        # Workspace-wide summary
        all_projects = await db.execute(
            select(Project).options(selectinload(Project.tasks))
        )
        projects = all_projects.scalars().all()
        context = f"Workspace has {len(projects)} projects.\n"
        for p in projects[:20]:  # cap at 20 for token budget
            context += f"- [{p.status}] {p.title} | Priority: {p.priority} | Progress: {p.progress_pct}%\n"
            if p.blockers:
                context += f"  Blocked: {p.blockers}\n"

    body = await chat_completion(
        system_prompt=SUMMARY_SYSTEM,
        user_prompt=f"Generate a {payload.summary_type} summary.\n\nContext:\n{context}",
        temperature=0.4,
    )

    entity_id = payload.entity_id or UUID("00000000-0000-0000-0000-000000000000")
    summary = AISummary(
        entity_type=payload.entity_type,
        entity_id=entity_id,
        summary_type=payload.summary_type,
        body=body,
    )
    db.add(summary)
    await db.commit()

    return {"summary": body, "summary_type": payload.summary_type}


# ── Priority Suggestion ───────────────────────────────────────────────────────

@router.post("/suggest-priority", response_model=PrioritySuggestionOut)
async def suggest_priority(
    payload: PrioritySuggestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == payload.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    today = date.today()
    days_until_due = (project.due_date - today).days if project.due_date else None
    context = f"""
Project: {project.title}
Description: {project.description or 'N/A'}
Current status: {project.status}
Current priority: {project.priority}
Progress: {project.progress_pct}%
Due date: {project.due_date} ({f'{days_until_due} days remaining' if days_until_due is not None else 'no due date'})
Blockers: {project.blockers or 'None'}
Risks: {project.risks or 'None'}
Tags: {', '.join(project.tags) if project.tags else 'None'}
Stakeholders: {', '.join(project.stakeholders) if project.stakeholders else 'None'}
"""

    ai_output: _PriorityAIOutput = await structured_completion(
        system_prompt=PRIORITY_SYSTEM,
        user_prompt=context,
        response_model=_PriorityAIOutput,
    )

    return PrioritySuggestionOut(
        suggested_priority=PriorityLevel(ai_output.suggested_priority),
        reasoning=ai_output.reasoning,
        factors=ai_output.factors,
    )


# ── Next Actions ──────────────────────────────────────────────────────────────

@router.post("/next-actions", response_model=dict)
async def suggest_next_actions(
    payload: PrioritySuggestionRequest,  # reuse — just needs project_id
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.tasks))
        .where(Project.id == payload.project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    incomplete_tasks = [t.title for t in project.tasks if not t.is_completed]
    context = f"""
Project: {project.title}
Status: {project.status} | Priority: {project.priority}
Progress: {project.progress_pct}% | Due: {project.due_date}
Blockers: {project.blockers or 'None'}
Next action currently recorded: {project.next_action or 'None'}
Incomplete tasks: {', '.join(incomplete_tasks) or 'None'}
"""
    NEXT_ACTION_SYSTEM = """You are PulseOps AI. Analyze the project state and recommend 3-5 concrete next actions.
Be specific, actionable, and ordered by priority. Focus on unblocking and moving the project forward.
Format as a numbered list."""

    actions = await chat_completion(
        system_prompt=NEXT_ACTION_SYSTEM,
        user_prompt=context,
        temperature=0.4,
    )
    return {"project_id": str(project.id), "next_actions": actions}


# ── AI Chat Assistant ─────────────────────────────────────────────────────────

class _ChatRequest(BaseModel):
    message: str
    project_id: Optional[str] = None
    history: List[dict] = []  # [{role: "user"|"assistant", content: str}]


class _IntentOutput(BaseModel):
    intent: str          # create_project | create_task | query | summarize
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None   # low/medium/high/urgent
    project_title: Optional[str] = None  # for task creation — which project
    proposed_tasks: Optional[List[dict]] = None  # for multi-task proposals


_INTENT_SYSTEM = """You are an intent classifier for a team project management assistant called PulseOps.

Classify the user message into one of these intents:
- create_project: user wants to create a new project
- create_task: user wants to create a task (possibly within a project)
- query: user is asking a question about their workspace, projects, tasks, meetings, team, or workload
- summarize: user wants a summary of projects, tasks, or activity

If the message is NOT related to project management, task tracking, team work, meetings, or the app itself, classify as:
- off_topic: anything unrelated — general knowledge, coding help, math, writing essays, recipes, jokes, weather, news, etc.

Also extract (for create_project / create_task only):
- title: a short clear title (max 8 words)
- description: a brief description (1-2 sentences)
- priority: low, medium, high, or urgent (infer from context; default medium)
- project_title: the name of the project the task belongs to (for create_task only)

Respond with JSON only."""

_MULTI_TASK_SYSTEM = """You are a task extraction assistant for a project management tool.
Extract ALL tasks mentioned in the user message.

For each task, return an object with:
- title: short clear title (max 10 words)
- description: brief description (1-2 sentences, or null)
- priority: exactly one of: low, medium, high, urgent (infer from context, default medium)
- assignee_name: person the task is assigned to (string or null)
- due_date_offset_days: number of days from today until due (integer or null)

Return a JSON object with a "tasks" array. Extract as many tasks as the message mentions.
If only one task is mentioned, return an array with one element."""


@router.post("/chat", response_model=dict)
async def ai_chat(
    payload: _ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Agentic AI assistant — understands intent and takes action."""

    # ── Step 1: classify intent ───────────────────────────────────────────────
    intent_result: _IntentOutput = await structured_completion(
        system_prompt=_INTENT_SYSTEM,
        user_prompt=payload.message,
        response_model=_IntentOutput,
        temperature=0.1,
    )

    # ── Step 2: act on intent ─────────────────────────────────────────────────

    # Refuse off-topic questions immediately — no LLM call needed
    if intent_result.intent == "off_topic":
        return {
            "reply": "I'm focused on your team's projects and tasks — I can't help with that here. "
                     "Try asking me about your projects, tasks, meetings, priorities, or team workload.",
            "action": "off_topic",
        }

    if intent_result.intent == "create_project":
        priority = intent_result.priority or "medium"
        if priority not in ("low", "medium", "high", "urgent"):
            priority = "medium"
        project = Project(
            title=intent_result.title or "New Project",
            description=intent_result.description or payload.message,
            status=ProjectStatus.intake,
            priority=PriorityLevel(priority),
            created_by=current_user.id,
            owner_id=current_user.id,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return {
            "reply": f"✅ Done! I created the project **\"{project.title}\"** with **{priority}** priority. You can find it on the Kanban board.",
            "action": "created_project",
            "project_id": str(project.id),
        }

    elif intent_result.intent == "create_task":
        # Find the project if mentioned
        target_project = None
        if intent_result.project_title:
            res = await db.execute(
                select(Project).where(Project.title.ilike(f"%{intent_result.project_title}%")).limit(1)
            )
            target_project = res.scalar_one_or_none()

        if not target_project and payload.project_id:
            res = await db.execute(select(Project).where(Project.id == UUID(payload.project_id)))
            target_project = res.scalar_one_or_none()

        # Extract all tasks from the message via second structured completion
        multi_output: _MultiTaskOutput = await structured_completion(
            system_prompt=_MULTI_TASK_SYSTEM,
            user_prompt=payload.message,
            response_model=_MultiTaskOutput,
            temperature=0.2,
        )

        proposed_tasks = multi_output.tasks or []
        n = len(proposed_tasks)
        reply_text = f"I found {n} task{'s' if n != 1 else ''}. Select which ones to create:"

        return {
            "reply": reply_text,
            "action": "propose_tasks",
            "proposed_tasks": proposed_tasks,
            "project_id": str(target_project.id) if target_project else None,
        }

    # ── Step 3: query / summarize — build context and answer ─────────────────
    projects_res = await db.execute(
        select(Project).options(selectinload(Project.tasks)).order_by(Project.updated_at.desc()).limit(30)
    )
    projects = projects_res.scalars().all()

    if not projects:
        context = "The workspace is empty — no projects yet."
    else:
        blocked = [p for p in projects if p.status == "blocked"]
        urgent = [p for p in projects if p.priority == "urgent"]
        overdue = [p for p in projects if p.due_date and p.due_date < date.today() and p.status != "done"]
        context = f"Workspace: {len(projects)} projects | {len(blocked)} blocked | {len(urgent)} urgent | {len(overdue)} overdue\n\n"
        for p in projects[:20]:
            context += f"- [{p.status}] {p.title} | {p.priority} priority | {p.progress_pct}% done | due {p.due_date or 'none'}"
            if p.blockers:
                context += f" | BLOCKED: {p.blockers}"
            context += "\n"

    # Per-user task context — so task-focused prompts ("what should I focus on
    # today?") answer from the user's actual assigned work, not project summaries.
    tasks_res = await db.execute(
        select(Task)
        .options(selectinload(Task.project))
        .where(
            Task.assigned_to == current_user.id,
            Task.is_completed == False,
            Task.status != "cancelled",
        )
    )
    my_tasks = list(tasks_res.scalars().all())

    today = date.today()
    week_end = today + timedelta(days=7)
    # Aggregate counts over the FULL set BEFORE truncation, so the model is told
    # the true workload even when only the soonest tasks are listed. (Mirrors the
    # projects block above, which counts on the full list and displays [:20].)
    def _prio(t):
        return getattr(t.priority, "value", t.priority)

    total_open = len(my_tasks)
    overdue_n = sum(1 for t in my_tasks if t.due_date and t.due_date < today)
    due_today_n = sum(1 for t in my_tasks if t.due_date == today)
    due_week_n = sum(1 for t in my_tasks if t.due_date and today <= t.due_date < week_end)
    urgent_n = sum(1 for t in my_tasks if _prio(t) == "urgent")
    high_n = sum(1 for t in my_tasks if _prio(t) == "high")

    # Relevance order so priority work always surfaces in the listed window,
    # not just the soonest-dated: overdue first, then by priority, then due date
    # (undated last). Cap is generous so a normal personal backlog is never cut.
    _PRIO_RANK = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    my_tasks.sort(key=lambda t: (
        not (t.due_date and t.due_date < today),   # overdue first
        _PRIO_RANK.get(_prio(t), 2),               # then urgent/high
        t.due_date is None,                        # dated before undated
        t.due_date or date.max,                    # then soonest due
    ))
    shown = my_tasks[:40]

    if total_open:
        header = f"{total_open} open"
        if overdue_n:
            header += f", {overdue_n} overdue"
        if due_today_n:
            header += f", {due_today_n} due today"
        if due_week_n:
            header += f", {due_week_n} due within 7 days"
        if urgent_n:
            header += f", {urgent_n} urgent"
        if high_n:
            header += f", {high_n} high"
        context += f"\nYour tasks ({header}):\n"
        for t in shown:
            proj = t.project.title if t.project else "no project"
            if t.due_date is None:
                due = "no due date"
            elif t.due_date < today:
                due = f"OVERDUE (was due {t.due_date})"
            elif t.due_date == today:
                due = "due TODAY"
            else:
                due = f"due {t.due_date}"
            context += f"- {t.title} | {_prio(t)} priority | {due} | project: {proj}\n"
        if total_open > len(shown):
            context += f"...and {total_open - len(shown)} more open task(s) not listed (showing the {len(shown)} most relevant by overdue/priority/due-date). The counts above are complete.\n"
    else:
        context += "\nYou have no open assigned tasks.\n"

    CHAT_SYSTEM = """You are PulseOps AI, an assistant built exclusively for project and task management.
You have access to the user's workspace data below. The "Your tasks" section lists the
current user's own open tasks; when they ask what to focus on, what to prioritize, or what is
overdue or due soon, answer from that section first (overdue and due-today tasks come first).

Your scope is strictly limited to:
- Projects, tasks, deadlines, priorities, and blockers
- Team workload and assignments
- Meeting outcomes and action items
- Workspace summaries and status updates

If asked anything outside this scope (general knowledge, coding, writing, math, recipes, news, etc.)
respond with: "I'm focused on your team's work — I can't help with that here."

Answer questions about the workspace directly and concisely. Max 150 words.

Formatting (the UI renders Markdown):
- Lead with a short one-line summary sentence, then the details.
- Use "- " for bullet points. Put each item on its own line; never run multiple items together on one line.
- Use "**bold**" only for short section labels (e.g. "**Due today**"), not whole sentences.
- For grouped items, make the group a top-level bullet with a bold label, and indent each item beneath it with two spaces ("  - ").
- Separate sections with a blank line. Do not use tables or headings."""

    answer = await chat_completion(
        system_prompt=f"{CHAT_SYSTEM}\n\nContext:\n{context}",
        user_prompt=payload.message,
        temperature=0.4,
        history=payload.history[-20:] if payload.history else None,
    )
    return {"reply": answer}


# ── Task Deduplication + Smart Update Agent ──────────────────────────────────

class _DedupeTaskIn(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    project_name: Optional[str] = None


class _DedupeRequest(BaseModel):
    proposed_tasks: List[_DedupeTaskIn]
    context: Optional[str] = None   # meeting summary or transcript snippet


class _DedupeMatch(BaseModel):
    proposed_title: str
    match_type: str           # "duplicate" | "update" | "new"
    existing_task_id: Optional[str] = None
    existing_task_title: Optional[str] = None
    existing_task_status: Optional[str] = None
    confidence: float         # 0-1
    suggestion: str           # human-readable explanation
    suggested_action: str     # "skip" | "update_status" | "create" | "merge"
    suggested_status: Optional[str] = None   # if update_status


_DEDUPE_SYSTEM = """You are a task deduplication agent for a team project management tool.

Analyse each PROPOSED task against EXISTING tasks. Return a JSON object with key "matches" containing an array.

Each element in "matches" MUST have exactly these fields:
{
  "proposed_title": "<exact proposed task title>",
  "match_type": "duplicate" | "update" | "new",
  "existing_task_id": "<UUID string from existing list>" | null,
  "existing_task_title": "<title of matching existing task>" | null,
  "existing_task_status": "<status of matching existing task>" | null,
  "confidence": <float 0.0-1.0>,
  "suggestion": "<one sentence: what you found and why>",
  "suggested_action": "skip" | "update_status" | "create",
  "suggested_status": "done" | "in_progress" | null
}

Rules:
- "duplicate": proposed task is essentially the same as existing (even if worded differently). Use "skip".
- "update": the context implies an existing task changed status (e.g. feature was demoed = done). Use "update_status".
- "new": no close match found. Use "create".
- Be fuzzy with titles — "Fix CORS bug" == "Add CORS whitelist for Stephen"
- confidence above 0.75 = match found; below = probably new
- Return ALL proposed tasks in the array, even if they are new"""


@router.post("/check-duplicates", response_model=dict)
async def check_task_duplicates(
    payload: _DedupeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check proposed tasks against existing ones.
    Returns matches, duplicates, and smart update suggestions.
    User must confirm before anything is created or changed."""

    # Load all existing open tasks for this user's projects
    assigned_proj_ids = select(Task.project_id).where(Task.assigned_to == current_user.id).scalar_subquery()
    existing_res = await db.execute(
        select(Task)
        .where(
            Task.is_completed == False,
            Task.status != "cancelled",
            Task.project_id.in_(assigned_proj_ids),
        )
        .order_by(Task.created_at.desc())
        .limit(100)
    )
    existing_tasks = existing_res.scalars().all()

    if not existing_tasks:
        # No existing tasks — everything is new
        return {
            "matches": [
                {"proposed_title": t.title, "match_type": "new", "suggested_action": "create",
                 "confidence": 1.0, "suggestion": "No existing tasks to compare against."}
                for t in payload.proposed_tasks
            ],
            "summary": f"All {len(payload.proposed_tasks)} tasks are new.",
            "duplicates_found": 0,
            "updates_suggested": 0,
        }

    # Build context for the AI
    existing_list = "\n".join([
        f"- [{t.id}] \"{t.title}\" | status:{t.status.value} | priority:{t.priority.value}"
        + (f" | project:{t.project_id}" if t.project_id else "")
        for t in existing_tasks
    ])
    proposed_list = "\n".join([
        f"- \"{t.title}\"" + (f" | {t.description[:100]}" if t.description else "")
        for t in payload.proposed_tasks
    ])
    context_note = f"\nMeeting context:\n{payload.context[:500]}" if payload.context else ""

    user_prompt = f"""EXISTING TASKS ({len(existing_tasks)}):
{existing_list}

PROPOSED NEW TASKS ({len(payload.proposed_tasks)}):
{proposed_list}{context_note}

Analyse each proposed task against the existing list. Return a JSON array."""

    import json as _json
    from app.services.ai_service import client as _client, MODEL as _MODEL
    response = await _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _DEDUPE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    raw = response.choices[0].message.content
    try:
        parsed = _json.loads(raw)
        # Handle various response shapes
        if isinstance(parsed, list):
            matches = parsed
        elif isinstance(parsed, dict):
            matches = (
                parsed.get("matches") or
                parsed.get("tasks") or
                parsed.get("results") or
                list(parsed.values())[0] if parsed else []
            )
        else:
            matches = []
        # Ensure required fields exist on each match
        for m in matches:
            m.setdefault("match_type", "new")
            m.setdefault("suggested_action", "create" if m["match_type"] == "new" else "skip")
            m.setdefault("confidence", 0.9 if m["match_type"] != "new" else 0.5)
    except Exception as e:
        logging.warning(f"Dedup parse error: {e} — raw: {raw[:200]}")
        matches = [{"proposed_title": t.title, "match_type": "new", "suggested_action": "create", "confidence": 1.0, "suggestion": "Could not analyse — treating as new."} for t in payload.proposed_tasks]

    duplicates = sum(1 for m in matches if m.get("match_type") == "duplicate")
    updates = sum(1 for m in matches if m.get("match_type") == "update")
    new_tasks = sum(1 for m in matches if m.get("match_type") == "new")

    return {
        "matches": matches,
        "summary": f"Found {duplicates} duplicate(s), {updates} update suggestion(s), {new_tasks} new task(s).",
        "duplicates_found": duplicates,
        "updates_suggested": updates,
    }


class _ApplyDedupeRequest(BaseModel):
    """User has reviewed the suggestions and confirmed which to apply."""
    confirmations: List[dict]   # [{proposed_title, action: "skip"|"create"|"update_status", task_id?, new_status?}]
    project_id: Optional[str] = None


@router.post("/apply-dedup-decisions", response_model=dict, status_code=201)
async def apply_dedup_decisions(
    payload: _ApplyDedupeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply the user-confirmed deduplication decisions.
    - skip: don't create the task
    - create: create as new task
    - update_status: update existing task status"""

    created = []
    updated = []
    skipped = []

    for conf in payload.confirmations:
        action = conf.get("action", "create")
        title = conf.get("proposed_title", "")

        if action == "skip":
            skipped.append(title)

        elif action == "update_status" and conf.get("task_id"):
            from uuid import UUID as _UUID
            task_res = await db.execute(select(Task).where(Task.id == _UUID(conf["task_id"])))
            task = task_res.scalar_one_or_none()
            if task:
                new_status = conf.get("new_status", "done")
                task.status = ProjectStatus(new_status)
                if new_status == "done":
                    task.is_completed = True
                    from datetime import datetime as _dt
                    task.completed_at = _dt.utcnow()
                updated.append(f"{task.title} → {new_status}")

        elif action == "create":
            # Find project
            proj = None
            if payload.project_id:
                from uuid import UUID as _UUID2
                proj_res = await db.execute(select(Project).where(Project.id == _UUID2(payload.project_id)))
                proj = proj_res.scalar_one_or_none()
            if not proj:
                proj_res = await db.execute(select(Project).where(Project.title == "Task Planner App").limit(1))
                proj = proj_res.scalar_one_or_none()
            if proj:
                new_task = Task(
                    title=conf.get("proposed_title", "New task"),
                    description=conf.get("description"),
                    status=ProjectStatus.todo,
                    priority=PriorityLevel(conf.get("priority", "medium")),
                    project_id=proj.id,
                    assigned_to=current_user.id,
                    created_by=current_user.id,
                )
                db.add(new_task)
                created.append(title)

    await db.commit()
    return {
        "created": len(created),
        "updated": len(updated),
        "skipped": len(skipped),
        "created_titles": created,
        "updated_titles": updated,
        "skipped_titles": skipped,
        "message": f"Created {len(created)}, updated {len(updated)}, skipped {len(skipped)} tasks.",
    }


# ── Confirm Tasks (from chat proposals) ──────────────────────────────────────

@router.post("/confirm-tasks", response_model=dict, status_code=201)
async def confirm_tasks(
    payload: _ConfirmTasksRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create tasks from AI chat proposed tasks that the user confirmed."""
    # Resolve project
    target_project = None
    if payload.project_id:
        try:
            res = await db.execute(select(Project).where(Project.id == UUID(payload.project_id)))
            target_project = res.scalar_one_or_none()
        except Exception:
            pass

    if not target_project:
        target_project = Project(
            title="AI Assistant Tasks",
            description="Created by AI assistant",
            status=ProjectStatus.intake,
            priority=PriorityLevel.medium,
            created_by=current_user.id,
            owner_id=current_user.id,
        )
        db.add(target_project)
        await db.flush()

    created_tasks = []
    for item in payload.tasks:
        assignee_user = None
        if item.get("assignee_name"):
            assignee_user = await find_or_create_user_by_name(db, item["assignee_name"])

        due_date = None
        offset = item.get("due_date_offset_days")
        if offset is not None:
            try:
                due_date = date.today() + timedelta(days=int(offset))
            except (ValueError, TypeError):
                pass

        raw_priority = item.get("priority", "medium")
        if raw_priority not in ("low", "medium", "high", "urgent"):
            raw_priority = "medium"

        task = Task(
            project_id=target_project.id,
            title=item.get("title", "Untitled task"),
            description=item.get("description"),
            priority=PriorityLevel(raw_priority),
            status=ProjectStatus.todo,
            # No task is left unassigned: fall back to the creator.
            assigned_to=assignee_user.id if assignee_user else current_user.id,
            due_date=due_date,
            created_by=current_user.id,
        )
        db.add(task)
        created_tasks.append(task)

    await db.commit()

    task_outs = []
    for t in created_tasks:
        await db.refresh(t)
        res = await db.execute(
            select(Task).options(selectinload(Task.assignee), selectinload(Task.project)).where(Task.id == t.id)
        )
        task_outs.append(TaskOut.model_validate(res.scalar_one()))

    return {
        "tasks_created": len(task_outs),
        "tasks": [t.model_dump(mode="json") for t in task_outs],
        "project_id": str(target_project.id),
    }


# ── AI Insights ───────────────────────────────────────────────────────────────

@router.get("/insights/{project_id}", response_model=List[AIInsightOut])
async def get_insights(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AIInsight)
        .where(AIInsight.project_id == project_id, AIInsight.is_dismissed == False)
        .order_by(AIInsight.created_at.desc())
    )
    return [AIInsightOut.model_validate(i) for i in result.scalars().all()]


@router.delete("/insights/{insight_id}/dismiss", status_code=204)
async def dismiss_insight(
    insight_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(AIInsight).where(AIInsight.id == insight_id))
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    insight.is_dismissed = True
    await db.commit()
