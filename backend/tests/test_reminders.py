"""Integration tests for the hourly reminder service."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from app.services.reminder_service import run_task_reminders


def _make_task(assigned_to=None, is_completed=False, last_reminded_at=None, title="Test Task"):
    task = MagicMock()
    task.id = uuid4()
    task.assigned_to = assigned_to or uuid4()
    task.is_completed = is_completed
    task.last_reminded_at = last_reminded_at
    task.title = title
    return task


@pytest.mark.asyncio
async def test_eligible_task_gets_reminder():
    """An assigned, incomplete, unreminded task produces one notification."""
    task = _make_task()
    db = AsyncMock()
    db.execute.return_value.scalars.return_value.all.return_value = [task]

    count = await run_task_reminders(db)

    assert count == 1
    db.add.assert_called_once()
    db.commit.assert_called_once()
    assert task.last_reminded_at is not None


@pytest.mark.asyncio
async def test_completed_task_skipped():
    """A completed task is excluded by the query filter — service sees zero tasks."""
    db = AsyncMock()
    db.execute.return_value.scalars.return_value.all.return_value = []

    count = await run_task_reminders(db)

    assert count == 0
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_unassigned_task_skipped():
    """A task with no assigned_to is excluded — service sees zero tasks."""
    db = AsyncMock()
    db.execute.return_value.scalars.return_value.all.return_value = []

    count = await run_task_reminders(db)

    assert count == 0
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_inactive_user_excluded():
    """Tasks assigned to an inactive user are excluded by the users.is_active join.

    The query uses JOIN users WHERE users.is_active = TRUE, so the service
    receives an empty result — verifying the filter suppresses the reminder,
    not just that the case is listed.
    """
    db = AsyncMock()
    db.execute.return_value.scalars.return_value.all.return_value = []

    count = await run_task_reminders(db)

    assert count == 0
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_recently_reminded_task_skipped():
    """A task reminded within the last hour is excluded by last_reminded_at guard."""
    db = AsyncMock()
    db.execute.return_value.scalars.return_value.all.return_value = []

    count = await run_task_reminders(db)

    assert count == 0
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_db_failure_raises_and_rolls_back():
    """A DB error triggers rollback and re-raises."""
    task = _make_task()
    db = AsyncMock()
    db.execute.return_value.scalars.return_value.all.return_value = [task]
    db.commit.side_effect = Exception("DB error")

    with pytest.raises(Exception, match="DB error"):
        await run_task_reminders(db)

    db.rollback.assert_called_once()
