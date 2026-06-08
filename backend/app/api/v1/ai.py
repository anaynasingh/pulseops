"""
PulseOps — AI API Endpoints
All AI-powered analysis, extraction, and generation endpoints.
"""
from datetime import date, timedelta
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.models import (
    Project, Task, AIInsight, AISummary, RequestIntake, MeetingTranscript,
    EmailIngestion, ProjectHealth, User, IntakeStatus
)
import logging
logger = logging.getLogger(__name__)
from app.schemas.schemas import (
    IntakeRequest, IntakeResult, IntakeOut, IntakeConfirmRequest,
    EmailAnalysisRequest, EmailAnalysisResult, EmailIngestionOut,
    TranscriptAnalysisRequest, TranscriptAnalysisResult, TranscriptOut,
    SummaryRequest, SummaryOut,
    PrioritySuggestionRequest, PrioritySuggestionOut,
    ProjectOut, AIInsightOut, TaskOut,
    PriorityLevel, ProjectStatus
)
from app.core.deps import get_current_user
from app.services.ai_service import (
    structured_completion, chat_completion,
    INTAKE_SYSTEM, EMAIL_SYSTEM, TRANSCRIPT_SYSTEM,
    PRIORITY_SYSTEM, HEALTH_SYSTEM, SUMMARY_SYSTEM,
)
from app.services.embedding import embed_and_store, embed_and_store_bg
from app.services.user_service import find_or_create_user_by_name
from pydantic import BaseModel

router = APIRouter(prefix="/ai", tags=["ai"])


# ── Internal Pydantic models for structured AI outputs ────────────────────────

class _IntakeAIOutput(BaseModel):
    title: str
    description: str
    project_type: str
    suggested_tags: List[str]
    suggested_subtasks: List[str]
    suggested_next_steps: List[str]
    suggested_due_date: Optional[str] = None
    suggested_priority: str   # low/medium/high/urgent
    suggested_owners: List[str]
    suggested_stakeholders: List[str]
    ai_reasoning: str


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


@router.post("/intake/{intake_id}/confirm", response_model=ProjectOut, status_code=201)
async def confirm_intake(
    intake_id: UUID,
    payload: IntakeConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Human confirms (or adjusts) the AI-suggested intake and creates a real project.
    The confirmed_priority field is REQUIRED — ensuring human sign-off.
    """
    from datetime import datetime as dt
    try:
        intake_res = await db.execute(select(RequestIntake).where(RequestIntake.id == intake_id))
        intake = intake_res.scalar_one_or_none()
        if not intake:
            raise HTTPException(status_code=404, detail="Intake not found")
        if intake.intake_status != IntakeStatus.pending:
            raise HTTPException(status_code=409, detail="Intake already processed")

        project = Project(
            title=payload.title or intake.generated_title or "Untitled Project",
            description=payload.description or intake.generated_description,
            status=ProjectStatus.intake,
            priority=payload.confirmed_priority,  # ← Human-confirmed priority
            owner_id=payload.owner_id,
            team_id=payload.team_id,
            tags=intake.suggested_tags or [],
            due_date=intake.suggested_due_date,
            next_action=(intake.suggested_next_steps or [])[0] if intake.suggested_next_steps else None,
            created_by=current_user.id,
        )
        db.add(project)
        await db.flush()

        intake.intake_status = IntakeStatus.confirmed
        intake.user_confirmed_priority = payload.confirmed_priority
        intake.project_id = project.id
        intake.confirmed_by = current_user.id
        intake.confirmed_at = dt.utcnow()

        await db.commit()

        # Reload with all relationships needed to serialize ProjectOut
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
        return ProjectOut.model_validate(proj_res.scalar_one())

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
    await db.commit()
    await db.refresh(record)

    background_tasks.add_task(
        embed_and_store_bg, "meeting", record.id,
        f"{payload.title} {payload.raw_transcript[:2000]}",
        {"meeting_id": str(record.id), "title": payload.title},
    )

    return TranscriptOut.model_validate(record)


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
            assigned_to=assignee_user.id if assignee_user else None,
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
            select(Task).options(selectinload(Task.assignee)).where(Task.id == t.id)
        )
        task_outs.append(TaskOut.model_validate(res.scalar_one()))

    return {"tasks_created": len(task_outs), "tasks": [t.model_dump(mode="json") for t in task_outs]}


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


class _IntentOutput(BaseModel):
    intent: str          # create_project | create_task | query | summarize
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None   # low/medium/high/urgent
    project_title: Optional[str] = None  # for task creation — which project
    proposed_tasks: Optional[List[dict]] = None  # for multi-task proposals


_INTENT_SYSTEM = """You are an intent classifier for a project management assistant.
Classify the user message into one of these intents:
- create_project: user wants to create a new project
- create_task: user wants to create a task (possibly within a project)
- query: user is asking a question about their workspace
- summarize: user wants a summary

Also extract:
- title: a short clear title (max 8 words) for the project or task if applicable
- description: a brief description of what needs to be done (1-2 sentences)
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

    CHAT_SYSTEM = """You are PulseOps AI, an intelligent assistant in a project management platform.
You can see the user's workspace. Answer their question directly and concisely.
Be specific. Use bullet points where helpful. Max 150 words."""

    answer = await chat_completion(
        system_prompt=f"{CHAT_SYSTEM}\n\nContext:\n{context}",
        user_prompt=payload.message,
        temperature=0.4,
    )
    return {"reply": answer}


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
            assigned_to=assignee_user.id if assignee_user else None,
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
            select(Task).options(selectinload(Task.assignee)).where(Task.id == t.id)
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
