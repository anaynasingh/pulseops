"""Teams meeting-transcript poll: Graph ingestion -> GPT-4o extraction -> per-user proposals.

Every ~10 minutes (APScheduler in main.py, or POST /internal/run-transcript-poll)
each connected user's calendar is scanned for online meetings, new transcripts are
ingested into meeting_transcripts (globally deduped by graph_transcript_id - the
partial UNIQUE constraint is the guarantee), action items are extracted once per
transcript, and each user gets their own pending ProposedTask rows for the bell.

Serialization (R1-1): the scheduler callback and the internal endpoint share
poll_lock, and the APScheduler job registers with max_instances=1, so overlapping
executions in this single-process deploy are impossible.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text as sa_text

from app.db.session import AsyncSessionLocal
from app.models.models import MeetingTranscript, PriorityLevel, ProposedTask, User
from app.services import graph_service
from app.services.ai_service import TRANSCRIPT_SYSTEM, structured_completion

logger = logging.getLogger(__name__)

# Shared by the APScheduler callback and POST /internal/run-transcript-poll: a
# manual trigger during an active scheduled tick gets HTTP 409 instead of a
# second concurrent poll (single-process deploy; replica scale-out is Deferred).
poll_lock = asyncio.Lock()

# Cap the cleaned VTT fed to GPT-4o (~6k tokens) so a multi-hour meeting cannot
# blow the <10s extraction criterion or the model context limit.
TRANSCRIPT_CHAR_BUDGET = 24_000
ELISION_MARKER = "\n\n[... transcript truncated ...]\n\n"

# C2: a transcript belongs to the event occurrence whose start..start+24h window
# contains its createdDateTime (recurring series yield one row per occurrence).
OCCURRENCE_WINDOW = timedelta(hours=24)
# C3: per-tick scan window is [max(cursor - 1h overlap, now - 7 days), now].
SCAN_OVERLAP = timedelta(hours=1)
MAX_LOOKBACK = timedelta(days=7)
EXTRACTION_TIMEOUT_S = 30


def truncate_transcript(text: str, budget: int = TRANSCRIPT_CHAR_BUDGET) -> tuple[str, bool]:
    """Head+tail truncation: keep the first 75% and last 25% of the budget,
    joined with an elision marker. Returns (text, was_truncated)."""
    if len(text) <= budget:
        return text, False
    head = int(budget * 0.75)
    tail = budget - head
    return text[:head] + ELISION_MARKER + text[-tail:], True


def parse_graph_datetime(value: str) -> Optional[datetime]:
    """Parse Graph ISO datetimes ('2026-07-23T10:00:00.1234567Z') to aware UTC.
    Graph emits 7 fractional digits; fromisoformat accepts at most 6."""
    if not value:
        return None
    v = value.strip().replace("Z", "+00:00")
    if "." in v:
        head, _, frac = v.partition(".")
        tz = ""
        for sep in ("+", "-"):
            idx = frac.find(sep)
            if idx != -1:
                tz = frac[idx:]
                frac = frac[:idx]
                break
        v = f"{head}.{frac[:6]}{tz}"
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _valid_priority(raw: object) -> PriorityLevel:
    if isinstance(raw, str) and raw in ("low", "medium", "high", "urgent"):
        return PriorityLevel(raw)
    return PriorityLevel.medium


async def run_transcript_poll() -> dict:
    """One full poll tick over every connected, active user.

    Per-user failure isolation: one user's exception is caught, logged, and
    skips cursor advance for that user only - never aborting the batch.
    Callers own poll_lock; this function does not acquire it.
    """
    stats = {"users_polled": 0, "transcripts_ingested": 0, "proposed_created": 0}
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.m365_token_cache.isnot(None), User.is_active == True)  # noqa: E712
        )
        users = result.scalars().all()
        for user in users:
            poll_start = datetime.now(timezone.utc)
            try:
                token = await graph_service.acquire_user_token(db, user)
                if token is None:
                    logger.warning("transcript poll: no Graph token for user %s (skipped, cursor unchanged)", user.id)
                    continue
                stats["users_polled"] += 1
                await _poll_user(db, user, token, poll_start, stats)
                # C3: the cursor advances to the poll-start timestamp ONLY when
                # this user's entire iteration completed without exception.
                user.m365_last_transcript_poll = poll_start
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("transcript poll failed for user %s (cursor unchanged)", user.id)
    return stats


async def run_transcript_poll_locked() -> dict:
    """Scheduler entrypoint: waits on the shared lock (max_instances=1 makes
    scheduler-vs-scheduler overlap impossible; the lock covers manual triggers)."""
    async with poll_lock:
        return await run_transcript_poll()


async def _poll_user(db: AsyncSession, user: User, token: str, poll_start: datetime, stats: dict) -> None:
    window_start = poll_start - MAX_LOOKBACK
    cursor = user.m365_last_transcript_poll
    if cursor is not None:
        if cursor.tzinfo is None:
            cursor = cursor.replace(tzinfo=timezone.utc)
        window_start = max(cursor - SCAN_OVERLAP, window_start)

    events = await graph_service.list_calendar_events(token, _iso_z(window_start), _iso_z(poll_start))
    seen_meeting_ids: set[str] = set()

    for event in events:
        join_url = ((event.get("onlineMeeting") or {}).get("joinUrl") or "").strip()
        if not join_url:
            continue
        meeting_id = graph_service.meeting_id_from_join_url(join_url)
        if not meeting_id:
            continue
        seen_meeting_ids.add(meeting_id)

        occurrence_start = parse_graph_datetime((event.get("start") or {}).get("dateTime", ""))
        if occurrence_start is None:
            continue

        transcripts = await graph_service.list_meeting_transcripts(token, meeting_id)
        for entry in transcripts:
            created = parse_graph_datetime(entry.get("createdDateTime", ""))
            # C2: bind each transcript to THIS occurrence by its created window;
            # never rely on a default-latest pick.
            if created is None or not (occurrence_start <= created <= occurrence_start + OCCURRENCE_WINDOW):
                continue
            row = await _ensure_transcript_row(
                db, token, user, meeting_id, entry, event, occurrence_start, stats
            )
            if row is None:
                continue
            if row.extracted_at is None:
                await _extract_transcript(db, row)
            stats["proposed_created"] += await _fan_out_proposals(db, user, row)

    # R1-3: retry sweep decoupled from the calendar window - re-pick ingested
    # rows still unextracted (bounded by the 7-day age cap) and re-extract.
    stale_result = await db.execute(
        select(MeetingTranscript).where(
            MeetingTranscript.extracted_at.is_(None),
            MeetingTranscript.graph_transcript_id.isnot(None),
            MeetingTranscript.created_at > poll_start - MAX_LOOKBACK,
        )
    )
    for row in stale_result.scalars().all():
        await _extract_transcript(db, row)
        if row.extracted_at is None:
            continue
        # AMBIGUITY: recovery fan-out is scoped to users we can associate with
        # the transcript without extra Graph calls - the ingesting user and any
        # user whose current scan window still covers the meeting. Other
        # attendees whose scan passed while extraction was failing recover only
        # via the 1h overlap window.
        if row.uploaded_by == user.id or (row.graph_meeting_id or "") in seen_meeting_ids:
            stats["proposed_created"] += await _fan_out_proposals(db, user, row)


async def _ensure_transcript_row(
    db: AsyncSession,
    token: str,
    user: User,
    meeting_id: str,
    entry: dict,
    event: dict,
    occurrence_start: datetime,
    stats: dict,
) -> Optional[MeetingTranscript]:
    """Fetch-or-ingest the shared transcript row for a Graph transcript id.

    Dedup is constraint-backed: INSERT ... ON CONFLICT DO NOTHING against the
    partial UNIQUE index on graph_transcript_id, so when two concurrent polls
    race, the loser skips cleanly (never a bare check-then-insert).
    """
    graph_transcript_id = entry.get("id")
    if not graph_transcript_id:
        return None

    existing = await db.execute(
        select(MeetingTranscript).where(MeetingTranscript.graph_transcript_id == graph_transcript_id)
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        return row

    content = await graph_service.get_transcript_content(token, meeting_id, graph_transcript_id)
    if not content:
        return None
    content, was_truncated = truncate_transcript(content)

    title = (event.get("subject") or "Untitled meeting").strip() or "Untitled meeting"
    await db.execute(
        pg_insert(MeetingTranscript).values(
            title=title[:500],
            raw_transcript=content,
            source="teams-poll",
            meeting_date=occurrence_start.date(),
            uploaded_by=user.id,
            graph_transcript_id=graph_transcript_id,
            graph_meeting_id=meeting_id[:255],
            truncated=was_truncated,
            action_items=[],
            decisions=[],
            blockers=[],
            attendees=[],
            tasks_created=False,
        ).on_conflict_do_nothing(
            index_elements=[MeetingTranscript.graph_transcript_id],
            index_where=sa_text("graph_transcript_id IS NOT NULL"),
        )
    )
    await db.commit()

    refetched = await db.execute(
        select(MeetingTranscript).where(MeetingTranscript.graph_transcript_id == graph_transcript_id)
    )
    row = refetched.scalar_one_or_none()
    if row is not None and row.uploaded_by == user.id:
        stats["transcripts_ingested"] += 1
    return row


async def _extract_transcript(db: AsyncSession, row: MeetingTranscript) -> None:
    """Extraction runs at most once per transcript (C1): results persist on the
    shared row; success is stamped by extracted_at (R1-2 - a zero-action-item
    result is a terminal success). Timeout/model failure (C4) leaves
    extracted_at NULL for the next tick's retry and never aborts the batch."""
    from app.api.v1.ai import _TranscriptAIOutput

    user_prompt = f"""
Meeting title: {row.title}
Date: {row.meeting_date or 'Unknown'}
Source: teams-poll

Transcript:
\"\"\"{row.raw_transcript}\"\"\"
"""
    try:
        ai_output = await asyncio.wait_for(
            structured_completion(
                system_prompt=TRANSCRIPT_SYSTEM,
                user_prompt=user_prompt,
                response_model=_TranscriptAIOutput,
            ),
            timeout=EXTRACTION_TIMEOUT_S,
        )
    except Exception:
        logger.warning("extraction failed for transcript %s (will retry next tick)", row.id, exc_info=True)
        return

    row.summary = ai_output.summary
    row.action_items = ai_output.action_items
    row.decisions = ai_output.decisions
    row.blockers = ai_output.blockers
    row.attendees = ai_output.attendees
    row.extracted_at = datetime.now(timezone.utc)
    await db.commit()


async def _fan_out_proposals(db: AsyncSession, user: User, row: MeetingTranscript) -> int:
    """Create THIS user's pending proposals from the stored extraction, once.

    Idempotency (C1): gated on proposal-absence for (user_id, transcript_id),
    never on the transcript insert winning - so a second user attending the same
    meeting gets their own proposals from the one shared row, and reuse keys on
    extracted_at IS NOT NULL, never on action_items truthiness (R1-2)."""
    if row.extracted_at is None:
        return 0
    existing = await db.execute(
        select(ProposedTask.id)
        .where(ProposedTask.user_id == user.id, ProposedTask.transcript_id == row.id)
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return 0

    created = 0
    for item in row.action_items or []:
        if not isinstance(item, dict):
            continue
        title = (item.get("task") or "Untitled task").strip() or "Untitled task"
        owner = item.get("owner")
        deadline = item.get("deadline")
        db.add(ProposedTask(
            user_id=user.id,
            transcript_id=row.id,
            meeting_title=row.title,
            meeting_date=row.meeting_date,
            title=title[:500],
            description=f"From meeting: {row.title}. Owner: {owner or 'TBD'}. Deadline: {deadline or 'TBD'}",
            priority=_valid_priority(item.get("priority")),
            assignee_hint=(str(owner)[:255] if owner else None),
            status="pending",
        ))
        created += 1
    if created:
        await db.commit()
    return created
