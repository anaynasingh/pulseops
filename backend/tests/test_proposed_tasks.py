"""Unit tests for the proposed-tasks confirm contract and pre-add dedup."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1 import proposed_tasks as pt
from app.api.v1.proposed_tasks import (
    confirm_proposed_tasks, is_duplicate_title, normalize_title,
)
from app.models.models import PriorityLevel
from app.schemas.schemas import ProposedTasksConfirmRequest


# ── Normalized-title dedup (deterministic, not pgvector) ─────────────────────

def test_normalize_title_lower_strip_collapse():
    assert normalize_title("  Send   the Q3 Report!! ") == "send the q3 report"
    assert normalize_title("Send-the-Q3-report") == "send the q3 report"


def test_duplicate_exact_normalized_match():
    assert is_duplicate_title("Send the Q3 report", "send THE q3 Report!") is True


def test_duplicate_fuzzy_above_threshold():
    assert is_duplicate_title("Send the Q3 report to finance", "Send the Q3 reports to finance") is True


def test_not_duplicate_below_threshold():
    assert is_duplicate_title("Send the Q3 report", "Book flights for offsite") is False


def test_empty_titles_never_duplicate():
    assert is_duplicate_title("", "anything") is False
    assert is_duplicate_title("!!!", "???") is False


# ── Confirm endpoint contract ─────────────────────────────────────────────────

def _user():
    user = MagicMock()
    user.id = uuid4()
    return user


def _pending_proposal(title="Follow up with vendor"):
    p = MagicMock()
    p.id = uuid4()
    p.status = "pending"
    p.title = title
    p.description = "From meeting: Weekly sync."
    p.priority = PriorityLevel.medium
    p.transcript_id = None
    return p


@pytest.mark.asyncio
async def test_overlapping_ids_rejected_422_listing_offenders():
    """C7: any UUID in BOTH lists is a deterministic 422 naming the ids."""
    shared = uuid4()
    payload = ProposedTasksConfirmRequest(accepted_ids=[shared], dismissed_ids=[shared, uuid4()])
    with pytest.raises(HTTPException) as exc:
        await confirm_proposed_tasks(payload, db=AsyncMock(), current_user=_user())
    assert exc.value.status_code == 422
    assert str(shared) in str(exc.value.detail)


@pytest.mark.asyncio
async def test_empty_lists_is_a_no_op():
    """Explicit-lists semantics: nothing named, nothing touched - pending
    proposals left off both lists stay pending."""
    db = AsyncMock()
    out = await confirm_proposed_tasks(
        ProposedTasksConfirmRequest(), db=db, current_user=_user()
    )
    assert out.created == 0 and out.dismissed == 0 and out.skipped_duplicates == 0
    assert out.results == []
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_id_reports_not_found():
    db = AsyncMock()
    db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    missing = uuid4()
    out = await confirm_proposed_tasks(
        ProposedTasksConfirmRequest(accepted_ids=[missing]), db=db, current_user=_user()
    )
    assert out.created == 0
    assert out.results[0].outcome == "not_found"
    assert out.results[0].proposed_id == missing


@pytest.mark.asyncio
async def test_already_handled_proposal_not_reprocessed():
    handled = _pending_proposal()
    handled.status = "accepted"
    db = AsyncMock()
    db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=handled))
    out = await confirm_proposed_tasks(
        ProposedTasksConfirmRequest(dismissed_ids=[handled.id]), db=db, current_user=_user()
    )
    assert out.dismissed == 0
    assert out.results[0].outcome == "already_handled"
    assert handled.status == "accepted"  # untouched


@pytest.mark.asyncio
async def test_dismiss_marks_proposal_dismissed():
    proposal = _pending_proposal()
    db = AsyncMock()
    db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=proposal))
    out = await confirm_proposed_tasks(
        ProposedTasksConfirmRequest(dismissed_ids=[proposal.id]), db=db, current_user=_user()
    )
    assert out.dismissed == 1
    assert out.results[0].outcome == "dismissed"
    assert proposal.status == "dismissed"
    assert proposal.handled_at is not None
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_accept_duplicate_title_skips_task_creation():
    """Pre-add dedup: a near-identical existing task title in the resolved
    project skips creation and records the existing task id."""
    user = _user()
    proposal = _pending_proposal(title="Send the Q3 report")
    project = MagicMock()
    project.id = uuid4()
    existing_task = MagicMock()
    existing_task.id = uuid4()

    results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=proposal)),      # load proposal
        MagicMock(scalar_one_or_none=MagicMock(return_value=project)),       # resolve request project
        MagicMock(all=MagicMock(return_value=[("send THE Q3 Report!!",)])),  # existing titles
        MagicMock(scalar_one_or_none=MagicMock(return_value=existing_task)), # fetch duplicate task
    ]
    db = AsyncMock()
    db.execute.side_effect = results

    with patch.object(pt, "recalc_project_progress", AsyncMock()):
        out = await confirm_proposed_tasks(
            ProposedTasksConfirmRequest(accepted_ids=[proposal.id], project_id=project.id),
            db=db, current_user=user,
        )

    assert out.created == 0
    assert out.skipped_duplicates == 1
    assert out.results[0].outcome == "skipped_duplicate"
    assert out.results[0].task_id == existing_task.id
    assert proposal.status == "accepted"
    assert proposal.dedup_status == "skipped_duplicate"
    assert proposal.dedup_existing_task_id == existing_task.id
    db.add.assert_not_called()  # no Task row created


@pytest.mark.asyncio
async def test_accept_unique_title_creates_task_and_recalcs_once():
    """Happy path: task created under the resolved project, proposal marked
    accepted with created_task_id, recalc runs post-commit once per project."""
    from app.models.models import Task, ProjectStatus

    user = _user()
    proposal = _pending_proposal(title="Book the offsite venue")
    project = MagicMock()
    project.id = uuid4()
    reloaded = Task(
        id=uuid4(), project_id=project.id, title=proposal.title,
        description=proposal.description, status=ProjectStatus.todo,
        priority=PriorityLevel.medium, assigned_to=user.id, created_by=user.id,
        is_completed=False, is_private=False,
        created_at=datetime.now(timezone.utc),
    )
    results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=proposal)),  # load proposal
        MagicMock(scalar_one_or_none=MagicMock(return_value=project)),   # resolve request project
        MagicMock(all=MagicMock(return_value=[("Unrelated task",)])),    # existing titles
        MagicMock(scalar_one=MagicMock(return_value=reloaded)),          # reload for TaskOut
    ]
    db = AsyncMock()
    db.execute.side_effect = results

    async def flush_assigns_id():
        for call in db.add.call_args_list:
            obj = call.args[0]
            if isinstance(obj, Task) and obj.id is None:
                obj.id = reloaded.id

    db.flush.side_effect = flush_assigns_id

    recalc = AsyncMock()
    with patch.object(pt, "recalc_project_progress", recalc):
        out = await confirm_proposed_tasks(
            ProposedTasksConfirmRequest(accepted_ids=[proposal.id], project_id=project.id),
            db=db, current_user=user,
        )

    assert out.created == 1
    assert out.results[0].outcome == "created"
    assert out.results[0].task_id == reloaded.id
    assert proposal.status == "accepted"
    assert proposal.created_task_id == reloaded.id
    assert proposal.dedup_status == "unique"
    assert out.tasks[0].title == "Book the offsite venue"
    recalc.assert_awaited_once_with(project.id)
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_partial_triage_only_named_ids_are_touched():
    """One accepted, one dismissed, a third pending proposal never named -
    only the two named ids appear in results (the third stays pending because
    the endpoint never queries beyond the explicit lists)."""
    user = _user()
    dismissed = _pending_proposal()
    db = AsyncMock()
    results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),       # accepted: not found
        MagicMock(scalar_one_or_none=MagicMock(return_value=dismissed)),  # dismissed: found
    ]
    db.execute.side_effect = results
    accepted_missing = uuid4()
    out = await confirm_proposed_tasks(
        ProposedTasksConfirmRequest(accepted_ids=[accepted_missing], dismissed_ids=[dismissed.id]),
        db=db, current_user=user,
    )
    assert len(out.results) == 2
    assert {r.outcome for r in out.results} == {"not_found", "dismissed"}
    assert db.execute.call_count == 2  # nothing beyond the named ids
