"""Unit tests for the transcript poll service and Graph helpers."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services import graph_service, transcript_poll_service
from app.services.transcript_poll_service import (
    ELISION_MARKER, TRANSCRIPT_CHAR_BUDGET,
    parse_graph_datetime, run_transcript_poll, truncate_transcript,
)


# ── VTT cleaning and meeting-id porting ───────────────────────────────────────

def test_clean_vtt_extracts_speaker_lines():
    vtt = (
        "WEBVTT\n\n1\n00:00:01.000 --> 00:00:03.000\n"
        "<v Alice Smith>We need the report by Friday.</v>\n"
        "2\n00:00:04.000 --> 00:00:06.000\n"
        "<v Bob Jones>I'll own that.</v>\n"
    )
    out = graph_service.clean_vtt(vtt)
    assert "Alice Smith: We need the report by Friday." in out
    assert "Bob Jones: I'll own that." in out
    assert "WEBVTT" not in out
    assert "-->" not in out


def test_meeting_id_from_join_url_roundtrip():
    import base64
    join = (
        "https://teams.microsoft.com/l/meetup-join/"
        "19%3ameeting_abc123%40thread.v2/0"
        "?context=%7b%22Tid%22%3a%22t1%22%2c%22Oid%22%3a%22oid-42%22%7d"
    )
    mid = graph_service.meeting_id_from_join_url(join)
    assert mid is not None
    assert base64.b64decode(mid).decode() == "1*oid-42*0**19:meeting_abc123@thread.v2"


def test_meeting_id_from_join_url_garbage_returns_none():
    assert graph_service.meeting_id_from_join_url("https://example.com/nope") is None


# ── Truncation (VTT char budget) ──────────────────────────────────────────────

def test_truncate_under_budget_unchanged():
    text, truncated = truncate_transcript("short transcript")
    assert text == "short transcript"
    assert truncated is False


def test_truncate_over_budget_head_tail_split():
    src = "A" * 20_000 + "B" * 20_000
    text, truncated = truncate_transcript(src)
    assert truncated is True
    head_budget = int(TRANSCRIPT_CHAR_BUDGET * 0.75)
    tail_budget = TRANSCRIPT_CHAR_BUDGET - head_budget
    assert len(text) == TRANSCRIPT_CHAR_BUDGET + len(ELISION_MARKER)
    assert text.startswith("A" * head_budget)
    assert text.endswith("B" * tail_budget)
    assert ELISION_MARKER in text


# ── Graph datetime parsing ────────────────────────────────────────────────────

def test_parse_graph_datetime_seven_fraction_digits():
    dt = parse_graph_datetime("2026-07-23T10:00:00.1234567Z")
    assert dt == datetime(2026, 7, 23, 10, 0, 0, 123456, tzinfo=timezone.utc)


def test_parse_graph_datetime_naive_coerced_utc():
    dt = parse_graph_datetime("2026-07-23T10:00:00.0000000")
    assert dt is not None and dt.tzinfo is not None


def test_parse_graph_datetime_empty_and_garbage():
    assert parse_graph_datetime("") is None
    assert parse_graph_datetime("not-a-date") is None


# ── calendarView pagination (R1-4) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calendar_events_follow_next_link_until_exhausted():
    page1 = MagicMock(status_code=200)
    page1.json.return_value = {"value": [{"id": "e1"}], "@odata.nextLink": "https://graph/next2"}
    page2 = MagicMock(status_code=200)
    page2.json.return_value = {"value": [{"id": "e2"}], "@odata.nextLink": "https://graph/next3"}
    page3 = MagicMock(status_code=200)
    page3.json.return_value = {"value": [{"id": "e3"}]}
    with patch.object(graph_service, "graph_request", AsyncMock(side_effect=[page1, page2, page3])) as req:
        events = await graph_service.list_calendar_events("tok", "2026-07-16T00:00:00Z", "2026-07-23T00:00:00Z")
    assert [e["id"] for e in events] == ["e1", "e2", "e3"]
    assert req.await_count == 3


@pytest.mark.asyncio
async def test_calendar_events_non_200_raises():
    err = MagicMock(status_code=403, text="denied")
    with patch.object(graph_service, "graph_request", AsyncMock(return_value=err)):
        with pytest.raises(RuntimeError):
            await graph_service.list_calendar_events("tok", "a", "b")


# ── Poll cursor semantics (C3) and per-user failure isolation ────────────────

def _fake_session_factory(db):
    @asynccontextmanager
    async def factory():
        yield db
    return factory


def _result(scalar=None, rows=None):
    """A sync result object (AsyncMock.return_value defaults to AsyncMock,
    whose method calls return coroutines - explicitly use MagicMock)."""
    m = MagicMock()
    m.scalar_one_or_none.return_value = scalar
    m.scalars.return_value.all.return_value = rows if rows is not None else []
    return m


def _connected_user(cursor=None):
    user = MagicMock()
    user.id = uuid4()
    user.m365_token_cache = "enc"
    user.m365_last_transcript_poll = cursor
    return user


@pytest.mark.asyncio
async def test_clean_iteration_advances_cursor():
    user = _connected_user()
    db = AsyncMock()
    db.execute.side_effect = [_result(rows=[user.id]), _result(scalar=user)]
    with patch.object(transcript_poll_service, "AsyncSessionLocal", _fake_session_factory(db)), \
         patch.object(transcript_poll_service.graph_service, "acquire_user_token", AsyncMock(return_value="tok")), \
         patch.object(transcript_poll_service, "_poll_user", AsyncMock()) as poll_user:
        stats = await run_transcript_poll()
    assert poll_user.await_count == 1
    assert user.m365_last_transcript_poll is not None
    assert stats["users_polled"] == 1
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_failed_iteration_preserves_cursor_and_continues_batch():
    """One user's exception is isolated: their cursor is unchanged, the other
    user still completes and advances."""
    old_cursor = datetime(2026, 7, 20, tzinfo=timezone.utc)
    failing = _connected_user(cursor=old_cursor)
    healthy = _connected_user()
    db = AsyncMock()
    db.execute.side_effect = [
        _result(rows=[failing.id, healthy.id]),
        _result(scalar=failing),
        _result(scalar=healthy),
    ]

    async def poll_side_effect(db_, user, *a, **k):
        if user is failing:
            raise RuntimeError("graph 500")

    with patch.object(transcript_poll_service, "AsyncSessionLocal", _fake_session_factory(db)), \
         patch.object(transcript_poll_service.graph_service, "acquire_user_token", AsyncMock(return_value="tok")), \
         patch.object(transcript_poll_service, "_poll_user", AsyncMock(side_effect=poll_side_effect)):
        stats = await run_transcript_poll()

    assert failing.m365_last_transcript_poll == old_cursor
    assert healthy.m365_last_transcript_poll is not None
    assert stats["users_polled"] == 2
    db.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_missing_token_skips_user_without_cursor_advance():
    user = _connected_user(cursor=None)
    db = AsyncMock()
    db.execute.side_effect = [_result(rows=[user.id]), _result(scalar=user)]
    with patch.object(transcript_poll_service, "AsyncSessionLocal", _fake_session_factory(db)), \
         patch.object(transcript_poll_service.graph_service, "acquire_user_token", AsyncMock(return_value=None)), \
         patch.object(transcript_poll_service, "_poll_user", AsyncMock()) as poll_user:
        stats = await run_transcript_poll()
    poll_user.assert_not_awaited()
    assert user.m365_last_transcript_poll is None
    assert stats["users_polled"] == 0


# ── Occurrence binding (C2) ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_only_transcripts_in_occurrence_window_are_ingested():
    user = _connected_user()
    db = AsyncMock()
    db.execute.return_value = _result(rows=[])  # retry sweep: none
    event = {
        "subject": "Weekly sync",
        "start": {"dateTime": "2026-07-22T10:00:00.0000000", "timeZone": "UTC"},
        "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/l/meetup-join/19%3am%40thread.v2/0?context=%7b%22Oid%22%3a%22o1%22%7d"},
    }
    in_window = {"id": "t-in", "createdDateTime": "2026-07-22T12:00:00.0000000Z"}
    out_of_window = {"id": "t-out", "createdDateTime": "2026-07-25T12:00:00.0000000Z"}
    ensured = AsyncMock(return_value=None)
    with patch.object(transcript_poll_service.graph_service, "list_calendar_events", AsyncMock(return_value=[event])), \
         patch.object(transcript_poll_service.graph_service, "list_meeting_transcripts", AsyncMock(return_value=[in_window, out_of_window])), \
         patch.object(transcript_poll_service, "_ensure_transcript_row", ensured):
        await transcript_poll_service._poll_user(
            db, user, "tok", datetime(2026, 7, 23, tzinfo=timezone.utc),
            {"users_polled": 0, "transcripts_ingested": 0, "proposed_created": 0},
        )
    assert ensured.await_count == 1
    assert ensured.await_args.args[4]["id"] == "t-in"


@pytest.mark.asyncio
async def test_extraction_attempted_at_most_once_per_tick():
    """A transcript whose extraction failed in the calendar loop is not re-sent
    to GPT-4o by the retry sweep in the same tick (peer-review finding)."""
    user = _connected_user()
    stale_row = MagicMock()
    stale_row.id = uuid4()
    stale_row.extracted_at = None
    db = AsyncMock()
    db.execute.return_value = _result(rows=[stale_row])  # retry sweep picks it
    extract = AsyncMock()
    with patch.object(transcript_poll_service.graph_service, "list_calendar_events", AsyncMock(return_value=[])), \
         patch.object(transcript_poll_service, "_extract_transcript", extract):
        await transcript_poll_service._poll_user(
            db, user, "tok", datetime(2026, 7, 23, tzinfo=timezone.utc),
            {"users_polled": 0, "transcripts_ingested": 0, "proposed_created": 0},
            attempted_extractions={stale_row.id},
        )
    extract.assert_not_awaited()


# ── Proposal fan-out idempotency (C1 / R1-2) ─────────────────────────────────

def _extracted_row(action_items, extracted=True):
    row = MagicMock()
    row.id = uuid4()
    row.title = "Weekly sync"
    row.meeting_date = None
    row.extracted_at = datetime.now(timezone.utc) if extracted else None
    row.action_items = action_items
    return row


@pytest.mark.asyncio
async def test_fan_out_skipped_when_not_extracted():
    db = AsyncMock()
    user = _connected_user()
    created = await transcript_poll_service._fan_out_proposals(db, user, _extracted_row([], extracted=False))
    assert created == 0
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_fan_out_skipped_when_user_already_has_proposals():
    db = AsyncMock()
    db.execute.return_value = _result(scalar=uuid4())  # absence check hits
    user = _connected_user()
    row = _extracted_row([{"task": "Do it", "owner": "Bob", "priority": "high"}])
    created = await transcript_poll_service._fan_out_proposals(db, user, row)
    assert created == 0
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_fan_out_creates_one_proposal_per_action_item():
    db = AsyncMock()
    db.execute.return_value = _result(scalar=None)
    user = _connected_user()
    row = _extracted_row([
        {"task": "Send report", "owner": "Alice", "deadline": "2026-07-25", "priority": "high"},
        {"task": "Book room", "owner": None, "priority": "not-a-priority"},
    ])
    created = await transcript_poll_service._fan_out_proposals(db, user, row)
    assert created == 2
    assert db.add.call_count == 2
    db.commit.assert_awaited()
    first = db.add.call_args_list[0].args[0]
    assert first.title == "Send report"
    assert first.assignee_hint == "Alice"
    assert first.status == "pending"


@pytest.mark.asyncio
async def test_zero_action_item_extraction_is_terminal_no_proposals():
    """R1-2: a zero-item success (extracted_at set, action_items=[]) creates no
    proposals and is not retried as a failure."""
    db = AsyncMock()
    db.execute.return_value = _result(scalar=None)
    user = _connected_user()
    row = _extracted_row([])
    created = await transcript_poll_service._fan_out_proposals(db, user, row)
    assert created == 0
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


# ── Extraction timeout (C4) ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extraction_timeout_leaves_extracted_at_null():
    db = AsyncMock()
    row = _extracted_row([], extracted=False)
    row.raw_transcript = "Alice: hello"

    async def slow(*a, **k):
        await asyncio.sleep(5)

    with patch.object(transcript_poll_service, "structured_completion", slow), \
         patch.object(transcript_poll_service, "EXTRACTION_TIMEOUT_S", 0.01):
        await transcript_poll_service._extract_transcript(db, row)
    assert row.extracted_at is None
    db.commit.assert_not_awaited()


# ── Poll serialization (R1-1) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_internal_trigger_409_while_poll_running():
    from app.api.v1.internal import trigger_transcript_poll
    async with transcript_poll_service.poll_lock:
        with pytest.raises(HTTPException) as exc:
            await trigger_transcript_poll(_=None)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_internal_trigger_runs_poll_when_free():
    from app.api.v1.internal import trigger_transcript_poll
    with patch("app.services.transcript_poll_service.run_transcript_poll",
               AsyncMock(return_value={"users_polled": 0, "transcripts_ingested": 0, "proposed_created": 0})):
        result = await trigger_transcript_poll(_=None)
    assert result == {"users_polled": 0, "transcripts_ingested": 0, "proposed_created": 0}
    assert not transcript_poll_service.poll_lock.locked()


# ── CRON_SECRET optionality (C6) ─────────────────────────────────────────────

def test_no_cron_secret_configured_returns_401():
    from app.api.v1.internal import _verify_cron_secret
    with patch("app.api.v1.internal.settings") as mock_settings:
        mock_settings.CRON_SECRET = None
        with pytest.raises(HTTPException) as exc:
            _verify_cron_secret(x_cron_secret="anything")
    assert exc.value.status_code == 401


def test_wrong_cron_secret_401_right_secret_passes():
    from app.api.v1.internal import _verify_cron_secret
    with patch("app.api.v1.internal.settings") as mock_settings:
        mock_settings.CRON_SECRET = "s3cret"
        with pytest.raises(HTTPException):
            _verify_cron_secret(x_cron_secret="wrong")
        assert _verify_cron_secret(x_cron_secret="s3cret") is None
