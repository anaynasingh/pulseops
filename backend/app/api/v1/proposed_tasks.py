"""Proposed-tasks bell API: list/count pending proposals, confirm/dismiss them.

Confirm semantics (Orchestrator ruling 2026-07-22): accepted_ids and
dismissed_ids are both EXPLICIT lists. A pending proposal named in neither list
stays pending in the bell for later triage - confirm never implicitly dismisses.
"""
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db_for_user, require_writer
from app.db.session import get_db
from app.models.models import (
    MeetingTranscript, PriorityLevel, Project, ProjectStatus, ProposedTask, Task, User,
)
from app.schemas.schemas import (
    ProposedTaskConfirmResult, ProposedTaskOut, ProposedTasksConfirmOut,
    ProposedTasksConfirmRequest, TaskOut,
)
from app.api.v1.tasks import _log_activity, recalc_project_progress

router = APIRouter(prefix="/proposed-tasks", tags=["proposed-tasks"])

DEDUP_SIMILARITY_THRESHOLD = 0.9
CATCHALL_PROJECT_TITLE = "Meeting Action Items"


def normalize_title(title: str) -> str:
    """lower(), strip non-alphanumeric, collapse whitespace - the deterministic
    pre-add dedup key (pgvector rejected: a live embedding round-trip per call
    is too slow/flaky for the pre-add gate)."""
    lowered = re.sub(r"[^a-z0-9\s]", " ", title.lower())
    return re.sub(r"\s+", " ", lowered).strip()


def is_duplicate_title(candidate: str, existing: str) -> bool:
    """Exact-normalized match OR SequenceMatcher ratio >= 0.9 on normalized forms."""
    a, b = normalize_title(candidate), normalize_title(existing)
    if not a or not b:
        return False
    if a == b:
        return True
    return SequenceMatcher(None, a, b).ratio() >= DEDUP_SIMILARITY_THRESHOLD


@router.get("/", response_model=List[ProposedTaskOut])
async def list_proposed_tasks(
    status_filter: str = Query("pending", alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ProposedTask)
        .where(ProposedTask.user_id == current_user.id, ProposedTask.status == status_filter)
        .order_by(ProposedTask.proposed_at.desc())
    )
    return [ProposedTaskOut.model_validate(p) for p in result.scalars().all()]


# FastAPI matches "/count" before the parameterless collection route regardless
# of order, but keep it above /confirm for readability.
@router.get("/count")
async def count_proposed_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(func.count()).select_from(ProposedTask).where(
            ProposedTask.user_id == current_user.id, ProposedTask.status == "pending"
        )
    )
    return {"pending": result.scalar() or 0}


async def _resolve_target_project(
    db: AsyncSession,
    current_user: User,
    request_project_id: Optional[UUID],
    transcript: Optional[MeetingTranscript],
) -> Project:
    """Fallback chain: request project -> transcript project -> auto-created
    per-user catch-all (mirrors ai.py::confirm_tasks)."""
    for candidate in (request_project_id, transcript.project_id if transcript else None):
        if candidate is None:
            continue
        result = await db.execute(select(Project).where(Project.id == candidate))
        project = result.scalar_one_or_none()
        if project:
            return project

    result = await db.execute(
        select(Project).where(
            Project.title == CATCHALL_PROJECT_TITLE, Project.owner_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()
    if project:
        return project

    project = Project(
        title=CATCHALL_PROJECT_TITLE,
        description="Action items confirmed from meeting transcripts",
        status=ProjectStatus.intake,
        priority=PriorityLevel.medium,
        created_by=current_user.id,
        owner_id=current_user.id,
    )
    db.add(project)
    await db.flush()
    return project


@router.post("/confirm", response_model=ProposedTasksConfirmOut, status_code=status.HTTP_201_CREATED)
async def confirm_proposed_tasks(
    payload: ProposedTasksConfirmRequest,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(require_writer),
):
    overlap = set(payload.accepted_ids) & set(payload.dismissed_ids)
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ids present in both accepted_ids and dismissed_ids: {sorted(str(i) for i in overlap)}",
        )

    now = datetime.now(timezone.utc)
    results: list[ProposedTaskConfirmResult] = []
    created_tasks: list[Task] = []
    skipped_duplicates = 0
    dismissed = 0
    # Per-project normalized-title pool; created titles are appended so two
    # near-identical accepted proposals in one batch dedup against each other.
    project_titles: dict[UUID, list[str]] = {}

    async def _load_proposal(proposed_id: UUID) -> Optional[ProposedTask]:
        result = await db.execute(
            select(ProposedTask).where(
                ProposedTask.id == proposed_id, ProposedTask.user_id == current_user.id
            )
        )
        return result.scalar_one_or_none()

    for proposed_id in payload.accepted_ids:
        proposal = await _load_proposal(proposed_id)
        if proposal is None:
            results.append(ProposedTaskConfirmResult(proposed_id=proposed_id, outcome="not_found"))
            continue
        if proposal.status != "pending":
            results.append(ProposedTaskConfirmResult(proposed_id=proposed_id, outcome="already_handled"))
            continue

        transcript = None
        if proposal.transcript_id:
            t_result = await db.execute(
                select(MeetingTranscript).where(MeetingTranscript.id == proposal.transcript_id)
            )
            transcript = t_result.scalar_one_or_none()
        project = await _resolve_target_project(db, current_user, payload.project_id, transcript)

        if project.id not in project_titles:
            titles_result = await db.execute(select(Task.title).where(Task.project_id == project.id))
            project_titles[project.id] = [t for (t,) in titles_result.all()]

        duplicate_of: Optional[Task] = None
        for existing_title in project_titles[project.id]:
            if is_duplicate_title(proposal.title, existing_title):
                dup_result = await db.execute(
                    select(Task).where(Task.project_id == project.id, Task.title == existing_title).limit(1)
                )
                duplicate_of = dup_result.scalar_one_or_none()
                break

        if duplicate_of is not None:
            proposal.status = "accepted"
            proposal.dedup_status = "skipped_duplicate"
            proposal.dedup_existing_task_id = duplicate_of.id
            proposal.handled_at = now
            skipped_duplicates += 1
            results.append(ProposedTaskConfirmResult(
                proposed_id=proposed_id, outcome="skipped_duplicate", task_id=duplicate_of.id
            ))
            continue

        task = Task(
            project_id=project.id,
            title=proposal.title,
            description=proposal.description,
            priority=proposal.priority,
            status=ProjectStatus.todo,
            # Assignee ruling: the confirming user, not resolved from the free-text
            # hint (avoids find_or_create_user_by_name side effects on bulk accept).
            assigned_to=current_user.id,
            due_date=None,
            created_by=current_user.id,
        )
        db.add(task)
        await db.flush()
        await _log_activity(db, task.id, current_user.id, "task_created", task.title)
        proposal.status = "accepted"
        proposal.created_task_id = task.id
        proposal.dedup_status = "unique"
        proposal.handled_at = now
        created_tasks.append(task)
        project_titles[project.id].append(task.title)
        results.append(ProposedTaskConfirmResult(proposed_id=proposed_id, outcome="created", task_id=task.id))

    for proposed_id in payload.dismissed_ids:
        proposal = await _load_proposal(proposed_id)
        if proposal is None:
            results.append(ProposedTaskConfirmResult(proposed_id=proposed_id, outcome="not_found"))
            continue
        if proposal.status != "pending":
            results.append(ProposedTaskConfirmResult(proposed_id=proposed_id, outcome="already_handled"))
            continue
        proposal.status = "dismissed"
        proposal.handled_at = now
        dismissed += 1
        results.append(ProposedTaskConfirmResult(proposed_id=proposed_id, outcome="dismissed"))

    await db.commit()

    # Post-commit (C8): recalc exactly once per affected project on a service
    # session, then bust the kanban cache so the board updates without reload.
    for project_id in {t.project_id for t in created_tasks}:
        await recalc_project_progress(project_id)
    if created_tasks:
        from app.api.v1.projects import _kanban_cache
        _kanban_cache.clear()

    task_outs: list[TaskOut] = []
    for task in created_tasks:
        result = await db.execute(
            select(Task).options(selectinload(Task.assignee), selectinload(Task.project)).where(Task.id == task.id)
        )
        task_outs.append(TaskOut.model_validate(result.scalar_one()))

    return ProposedTasksConfirmOut(
        created=len(created_tasks),
        skipped_duplicates=skipped_duplicates,
        dismissed=dismissed,
        tasks=task_outs,
        results=results,
    )
