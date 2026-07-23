"""Microsoft Graph access for the transcript poll (per-user delegated tokens).

Ports the calendarView + onlineMeetings transcript chain from
mcp-servers/m365/server.py, but parameterises every request by a per-user
access token acquired silently from that user's stored MSAL cache
(User.m365_token_cache, Fernet-encrypted) instead of a module-global token.
"""
import base64
import json
import logging
import re
from typing import Optional
from urllib.parse import quote, unquote, urlparse

import httpx
import msal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crypto import decrypt_str, encrypt_str
from app.models.models import User

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


async def acquire_user_token(db: AsyncSession, user: User) -> Optional[str]:
    """Silently acquire a Graph access token from the user's stored MSAL cache.

    Mirrors the token-refresh persistence contract in ai.py: if MSAL rotates the
    refresh token, the re-encrypted cache is committed so it never goes stale.
    Returns None when the user has no usable cache (caller treats as a per-user
    failure: skip the user, do not advance their cursor).
    """
    if not user.m365_token_cache:
        return None
    try:
        cache = msal.SerializableTokenCache()
        cache.deserialize(decrypt_str(user.m365_token_cache))
        from app.api.v1.auth import _msal_app
        app = _msal_app(cache)
        accounts = app.get_accounts()
        if not accounts:
            return None
        result = app.acquire_token_silent(settings.M365_GRAPH_SCOPES, account=accounts[0])
        if cache.has_state_changed:
            user.m365_token_cache = encrypt_str(cache.serialize())
            await db.commit()
        if not result or "access_token" not in result:
            return None
        return result["access_token"]
    except Exception:
        logger.warning("Could not acquire Graph token for user %s", user.id, exc_info=True)
        return None


async def graph_request(
    method: str,
    path_or_url: str,
    *,
    token: str,
    params: dict | None = None,
    json_body: dict | None = None,
) -> httpx.Response:
    """Authenticated Graph request. path_or_url may be a path or an absolute
    @odata.nextLink URL (pagination)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = path_or_url if path_or_url.startswith("http") else f"{GRAPH_BASE}{path_or_url}"
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.request(
            method, url, headers=headers, params=params, json=json_body, timeout=30
        )
    return resp


async def list_calendar_events(token: str, start_iso: str, end_iso: str) -> list[dict]:
    """All calendarView events overlapping [start, end].

    Pagination contract (R1-4): follows @odata.nextLink until exhausted ($top
    stays 50 per page) so a busy week's events are never silently truncated to
    the first page. Raises on a non-200 so the caller treats the whole user
    iteration as failed (cursor unchanged).
    """
    select = "id,subject,start,end,organizer,isOnlineMeeting,onlineMeeting"
    params = {
        "startDateTime": start_iso,
        "endDateTime": end_iso,
        "$select": select,
        "$orderby": "start/dateTime asc",
        "$top": 50,
    }
    events: list[dict] = []
    resp = await graph_request("GET", "/me/calendarView", token=token, params=params)
    while True:
        if resp.status_code != 200:
            raise RuntimeError(f"calendarView failed ({resp.status_code}): {resp.text[:300]}")
        body = resp.json()
        events.extend(body.get("value", []))
        next_link = body.get("@odata.nextLink")
        if not next_link:
            return events
        resp = await graph_request("GET", next_link, token=token)


async def list_meeting_transcripts(token: str, meeting_id_b64: str) -> list[dict]:
    """Transcript metadata entries for an online meeting (may span occurrences
    of a recurring series). Returns [] when the meeting has none or the id does
    not resolve (404) - both are normal, not failures."""
    q = quote(meeting_id_b64, safe="")
    resp = await graph_request("GET", f"/me/onlineMeetings/{q}/transcripts", token=token)
    if resp.status_code == 404:
        return []
    if resp.status_code != 200:
        raise RuntimeError(f"transcripts list failed ({resp.status_code}): {resp.text[:300]}")
    return resp.json().get("value", [])


async def get_transcript_content(token: str, meeting_id_b64: str, transcript_id: str) -> str:
    """Download one transcript as VTT and reduce it to 'Speaker: text' lines."""
    q = quote(meeting_id_b64, safe="")
    resp = await graph_request(
        "GET",
        f"/me/onlineMeetings/{q}/transcripts/{quote(transcript_id, safe='')}/content",
        token=token,
        params={"$format": "text/vtt"},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"transcript content failed ({resp.status_code}): {resp.text[:300]}")
    return clean_vtt(resp.text)


def clean_vtt(vtt: str) -> str:
    """Reduce a WebVTT transcript to readable 'Speaker: text' lines.
    Ported verbatim from mcp-servers/m365/server.py::_clean_vtt."""
    lines_out: list[str] = []
    last_speaker = None
    for raw in vtt.splitlines():
        line = raw.strip()
        if not line or line == "WEBVTT" or line.isdigit() or "-->" in line:
            continue
        # Teams tags speakers as <v Full Name>text</v>
        m = re.match(r"<v\s+([^>]+)>(.*?)</v>", line)
        if m:
            speaker, text = m.group(1).strip(), m.group(2).strip()
        else:
            speaker, text = None, re.sub(r"<[^>]+>", "", line).strip()
        if not text:
            continue
        if speaker and speaker != last_speaker:
            lines_out.append(f"\n{speaker}: {text}")
            last_speaker = speaker
        else:
            lines_out.append(text)
    return "\n".join(lines_out).strip()


def meeting_id_from_join_url(join_url: str) -> Optional[str]:
    """Construct the Graph onlineMeeting id straight from a Teams join URL.

    The id is base64('1*{organizerOid}*0**{threadId}'), where both parts are in
    the join URL. This lets an ATTENDEE read a meeting they did NOT organize -
    delegated OnlineMeetingTranscript.Read.All governs access - bypassing the
    organizer-only /me/onlineMeetings?$filter=JoinWebUrl lookup. For a recurring
    series (same join URL every week) this id returns every occurrence's transcript.
    Ported verbatim from mcp-servers/m365/server.py::_meeting_id_from_join_url.
    """
    try:
        p = urlparse(join_url)
        thread = unquote(p.path.split("/meetup-join/", 1)[1].split("/", 1)[0])  # 19:meeting_...@thread.v2
        ctx = json.loads(unquote(p.query.split("context=", 1)[1]))
        oid = ctx["Oid"]
        return base64.b64encode(f"1*{oid}*0**{thread}".encode()).decode()
    except Exception:
        return None
