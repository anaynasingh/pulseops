"""Hourly task reminder job — called by POST /api/v1/internal/run-reminders."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Task, User, Notification

logger = logging.getLogger(__name__)


async def run_task_reminders(db: AsyncSession) -> int:
    """Create reminder notifications for all eligible assigned tasks.

    Eligible: assigned to an active user, not completed, and not reminded
    within the last hour (last_reminded_at IS NULL or older than 1 hour).

    The notification insert and timestamp stamp are committed together in a
    single transaction so a partial failure leaves no orphaned reminder.

    Returns the count of reminders created.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

    try:
        result = await db.execute(
            select(Task)
            .join(User, Task.assigned_to == User.id)
            .where(
                Task.assigned_to.isnot(None),
                Task.is_completed == False,
                User.is_active == True,
                (Task.last_reminded_at == None) | (Task.last_reminded_at < cutoff),
            )
        )
        tasks = result.scalars().all()

        now = datetime.now(timezone.utc)
        for task in tasks:
            db.add(Notification(
                user_id=task.assigned_to,
                type="reminder",
                title=f"Reminder: {task.title}",
                body="This task is still open and assigned to you.",
                entity_type="task",
                entity_id=task.id,
            ))
            task.last_reminded_at = now

        await db.commit()
        logger.info("Reminder job: %d reminder(s) sent.", len(tasks))
        return len(tasks)
    except Exception:
        await db.rollback()
        logger.exception("Reminder job failed — transaction rolled back.")
        raise


async def run_block_reminders(db: AsyncSession) -> int:
    """Notify users when a scheduled time-block starts within the current hour.

    Eligible: assigned to an active user, not completed, scheduled_at falls in
    the current clock hour [hour_start, hour_start + 1h), and not already
    block-reminded for this scheduling (block_reminded_at IS NULL or earlier
    than scheduled_at — so rescheduling re-arms the reminder).

    Returns the count of block reminders created.
    """
    now = datetime.now(timezone.utc)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)

    try:
        result = await db.execute(
            select(Task)
            .join(User, Task.assigned_to == User.id)
            .where(
                Task.assigned_to.isnot(None),
                Task.is_completed == False,
                User.is_active == True,
                Task.scheduled_at.isnot(None),
                Task.scheduled_at >= hour_start,
                Task.scheduled_at < hour_end,
                (Task.block_reminded_at == None) | (Task.block_reminded_at < Task.scheduled_at),
            )
        )
        tasks = result.scalars().all()

        for task in tasks:
            db.add(Notification(
                user_id=task.assigned_to,
                type="block_reminder",
                title=f"Starting now: {task.title}",
                body="Your scheduled time block is starting.",
                entity_type="task",
                entity_id=task.id,
            ))
            task.block_reminded_at = now

        await db.commit()
        logger.info("Block reminder job: %d reminder(s) sent.", len(tasks))
        return len(tasks)
    except Exception:
        await db.rollback()
        logger.exception("Block reminder job failed — transaction rolled back.")
        raise
