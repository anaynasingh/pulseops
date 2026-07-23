"""Internal endpoints — only callable by trusted Railway Cron with CRON_SECRET."""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.config import settings
from app.services.reminder_service import run_task_reminders, run_block_reminders

router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_cron_secret(x_cron_secret: str = Header(default="")) -> None:
    if not settings.CRON_SECRET or x_cron_secret != settings.CRON_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@router.post("/run-reminders", status_code=200)
async def trigger_reminders(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_cron_secret),
):
    count = await run_task_reminders(db)
    block_count = await run_block_reminders(db)
    return {"reminders_sent": count, "block_reminders_sent": block_count}


@router.post("/run-transcript-poll", status_code=200)
async def trigger_transcript_poll(
    _: None = Depends(_verify_cron_secret),
):
    """Manual/cron trigger for the transcript poll. Serialized against the
    APScheduler tick via the shared lock (R1-1): a trigger during an active
    scheduled run returns 409 rather than starting a concurrent poll."""
    from app.services.transcript_poll_service import poll_lock, run_transcript_poll

    if poll_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A transcript poll is already running.",
        )
    async with poll_lock:
        return await run_transcript_poll()
