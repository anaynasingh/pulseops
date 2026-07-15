"""
Microsoft 365 MCP Server
Gives Claude access to Outlook email and calendar via Microsoft Graph API.
Uses MSAL device code flow for authentication (browser-based, one-time login).
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import msal
import requests
import urllib3
from dotenv import load_dotenv

# Corporate proxy SSL bypass — same pattern as the rest of the PulseOps stack
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_requests_session = requests.Session()
_requests_session.verify = False
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# ---------------------------------------------------------------------------
# Load env
# ---------------------------------------------------------------------------
load_dotenv()

CLIENT_ID = os.getenv("M365_CLIENT_ID", "")
TENANT_ID = os.getenv("M365_TENANT_ID", "common")
CLIENT_SECRET = os.getenv("M365_CLIENT_SECRET", "")  # optional

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
# Scopes are env-overridable so the transcript scope (which needs tenant-admin
# consent) can be dropped if consent isn't available — email/calendar/meetings
# still work without it. IMPORTANT: keep the server's scopes identical to what
# the cached token was minted with, or silent refresh re-triggers device flow.
_DEFAULT_SCOPES = (
    "Mail.Read Mail.ReadWrite Calendars.Read "
    "OnlineMeetings.Read OnlineMeetingTranscript.Read.All "
    # Files.Read.All / Sites.Read.All back the find_meeting_files & read_meeting_file
    # tools (reading transcript/recording files for meetings you didn't organize).
    "Files.Read.All Sites.Read.All"
)
SCOPES = os.getenv("M365_SCOPES", _DEFAULT_SCOPES).split()
# Token cache: on Railway point this at the mounted volume so it survives
# restarts (e.g. M365_TOKEN_CACHE=/data/.pulseops_m365_token.json).
TOKEN_CACHE_PATH = Path(
    os.getenv("M365_TOKEN_CACHE", str(Path.home() / ".pulseops_m365_token.json"))
)

# ---------------------------------------------------------------------------
# MSAL auth
# ---------------------------------------------------------------------------
_token_cache = msal.SerializableTokenCache()


def _seed_cache_from_env() -> None:
    """Materialize the token cache from M365_TOKEN_B64 on a fresh headless
    container. The value is base64 of a serialized MSAL cache produced locally
    by m365_login.py, so silent refresh works without an interactive login."""
    b64 = os.getenv("M365_TOKEN_B64", "").strip()
    if not b64 or TOKEN_CACHE_PATH.exists():
        return
    import base64
    try:
        TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_PATH.write_text(base64.b64decode(b64).decode("utf-8"), encoding="utf-8")
        print(f"Seeded M365 token cache from M365_TOKEN_B64 at {TOKEN_CACHE_PATH}", file=sys.stderr)
    except Exception as exc:
        print(f"WARNING: could not seed token cache from M365_TOKEN_B64: {exc}", file=sys.stderr)


def _load_cache() -> None:
    _seed_cache_from_env()
    if TOKEN_CACHE_PATH.exists():
        _token_cache.deserialize(TOKEN_CACHE_PATH.read_text(encoding="utf-8"))


def _save_cache() -> None:
    if _token_cache.has_state_changed:
        TOKEN_CACHE_PATH.write_text(_token_cache.serialize(), encoding="utf-8")


def _build_app() -> msal.ClientApplication:
    _load_cache()
    if CLIENT_SECRET:
        return msal.ConfidentialClientApplication(
            CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}",
            client_credential=CLIENT_SECRET,
            token_cache=_token_cache,
            http_client=_requests_session,
        )
    return msal.PublicClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        token_cache=_token_cache,
        http_client=_requests_session,
    )


def _get_token() -> str:
    """Return a valid access token, triggering device flow if needed."""
    app = _build_app()

    # Try silent first (uses cached token / refresh token)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_cache()
            return result["access_token"]

    # Fall back to device code flow — but never in a headless deploy, where it
    # would block forever (no one to enter the code). The bridge sets
    # M365_NO_DEVICE_FLOW=1; auth must be pre-seeded via M365_TOKEN_B64.
    if os.getenv("M365_NO_DEVICE_FLOW"):
        raise RuntimeError(
            "M365 is not authenticated and interactive device-code login is disabled "
            "in this environment. Run m365_login.py locally and set M365_TOKEN_B64 "
            "(and matching M365_SCOPES) on the service."
        )
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Failed to create device flow: {flow.get('error_description', flow)}")

    # Print the device code instructions to stderr so they appear in the terminal
    print("\n" + "=" * 60, file=sys.stderr)
    print("M365 Authentication Required", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(flow["message"], file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(
            f"Auth failed: {result.get('error_description', result.get('error', 'unknown'))}"
        )

    _save_cache()
    return result["access_token"]


async def _graph_request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> httpx.Response:
    """Make an authenticated Microsoft Graph request."""
    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{GRAPH_BASE}{path}"
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.request(
            method, url, headers=headers, params=params, json=json_body, timeout=30
        )
    return resp


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_datetime(dt_str: str) -> str:
    """Format an ISO datetime string to a readable local-ish format."""
    if not dt_str:
        return "unknown"
    try:
        # Handle both 'Z' suffix and '+00:00'
        dt_str_clean = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_str_clean)
        return dt.strftime("%a %b %d, %Y at %I:%M %p %Z").strip()
    except Exception:
        return dt_str[:19].replace("T", " ")


def _fmt_email(msg: dict, full_body: bool = False) -> str:
    """Format a single email message."""
    sender = msg.get("from", {})
    sender_name = sender.get("emailAddress", {}).get("name", "")
    sender_email = sender.get("emailAddress", {}).get("address", "")
    sender_str = f"{sender_name} <{sender_email}>" if sender_name else sender_email

    subject = msg.get("subject", "(no subject)")
    received = _fmt_datetime(msg.get("receivedDateTime", ""))
    is_read = msg.get("isRead", True)
    unread_marker = " [UNREAD]" if not is_read else ""

    lines = [
        f"{'—'*50}",
        f"ID:       {msg.get('id', '')}",
        f"From:     {sender_str}",
        f"Subject:  {subject}{unread_marker}",
        f"Date:     {received}",
    ]

    if full_body:
        body_content = msg.get("body", {})
        body_text = body_content.get("content", "")
        # Strip basic HTML tags for readability
        import re
        body_text = re.sub(r"<[^>]+>", "", body_text)
        body_text = re.sub(r"\n{3,}", "\n\n", body_text).strip()
        if body_text:
            lines.append(f"\nBody:\n{body_text[:3000]}")
            if len(body_text) > 3000:
                lines.append("  [... body truncated ...]")
    else:
        preview = msg.get("bodyPreview", "")
        if preview:
            lines.append(f"Preview:  {preview[:200]}")

    return "\n".join(lines)


def _fmt_event(event: dict) -> str:
    """Format a calendar event."""
    start_raw = event.get("start", {})
    end_raw = event.get("end", {})
    start_str = start_raw.get("dateTime", start_raw.get("date", ""))
    end_str = end_raw.get("dateTime", end_raw.get("date", ""))

    subject = event.get("subject", "(no title)")
    location = event.get("location", {}).get("displayName", "")
    organizer = event.get("organizer", {}).get("emailAddress", {})
    organizer_str = f"{organizer.get('name', '')} <{organizer.get('address', '')}>".strip(" <>")
    is_online = event.get("isOnlineMeeting", False)
    online_url = event.get("onlineMeeting", {}).get("joinUrl", "") if is_online else ""

    attendees = event.get("attendees", [])
    attendee_names = [
        a.get("emailAddress", {}).get("name", a.get("emailAddress", {}).get("address", ""))
        for a in attendees[:5]
    ]

    lines = [
        f"{'—'*50}",
        f"Event:    {subject}",
        f"Start:    {_fmt_datetime(start_str)}",
        f"End:      {_fmt_datetime(end_str)}",
    ]
    if location:
        lines.append(f"Location: {location}")
    if is_online and online_url:
        lines.append(f"Join:     {online_url}")
    if organizer_str.strip("<> "):
        lines.append(f"Organizer: {organizer_str}")
    if attendee_names:
        suffix = f" (+ {len(attendees)-5} more)" if len(attendees) > 5 else ""
        lines.append(f"Attendees: {', '.join(attendee_names)}{suffix}")

    return "\n".join(lines)


def _error(msg: str, status_code: int | None = None) -> str:
    code_str = f" (HTTP {status_code})" if status_code else ""
    return f"ERROR{code_str}: {msg}"


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
server = Server("m365")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_emails",
            description="List recent emails from Outlook inbox. Returns sender, subject, preview, date, and message ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Number of emails to return (default 20)", "default": 20},
                    "folder": {"type": "string", "description": "Folder to list from (default: inbox)", "default": "inbox"},
                    "search": {"type": "string", "description": "Optional search query to filter emails"},
                },
            },
        ),
        Tool(
            name="get_email",
            description="Get the full content of an email by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The Graph API message ID"},
                },
                "required": ["message_id"],
            },
        ),
        Tool(
            name="search_emails",
            description="Search emails by keyword across subject and body.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword or phrase"},
                    "count": {"type": "integer", "description": "Max results to return (default 10)", "default": 10},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_calendar_events",
            description=(
                "List calendar events from Outlook Calendar. Looks both backward and "
                "forward, so it includes meetings that already happened earlier today "
                "or in recent days (use this to find a past meeting to summarize or "
                "pull a transcript from)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "How many days ahead to look (default 7)", "default": 7},
                    "days_back": {"type": "integer", "description": "How many days back to look, including earlier today (default 7)", "default": 7},
                },
            },
        ),
        Tool(
            name="get_unread_emails",
            description="Get all unread emails from inbox.",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Max unread emails to return (default 10)", "default": 10},
                },
            },
        ),
        Tool(
            name="mark_email_read",
            description="Mark an email as read.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The Graph API message ID to mark as read"},
                },
                "required": ["message_id"],
            },
        ),
        Tool(
            name="get_my_profile",
            description="Get the current user's M365 profile (name, email, department).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_meeting_transcript",
            description=(
                "Fetch a Teams meeting transcript straight off a calendar event, returned "
                "as readable text to summarize and turn into action items. Call "
                "list_calendar_events first and pass the event's id (or its Teams join URL). "
                "Works even for meetings you did NOT organize, as long as you were invited "
                "and transcription was on. For a recurring series it returns the latest "
                "occurrence by default; pass on_date to pick a specific one (the response "
                "lists which occurrence dates are available)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "Calendar event ID from list_calendar_events."},
                    "join_url": {"type": "string", "description": "Teams meeting join URL (alternative to event_id)."},
                    "on_date": {"type": "string", "description": "Optional YYYY-MM-DD to pick a specific occurrence of a recurring meeting; defaults to the most recent."},
                },
            },
        ),
        Tool(
            name="find_meeting_files",
            description=(
                "Search OneDrive AND files shared with you (and SharePoint) for Teams "
                "meeting recordings/transcripts by keyword — e.g. the meeting subject "
                "like 'Dev Meeting'. Use this when get_meeting_transcript fails because "
                "you were NOT the organizer: recordings/transcripts of meetings others "
                "organized are usually shared to your OneDrive 'Shared with me'. Returns "
                "matching files with a drive_id + item_id you pass to read_meeting_file. "
                "Requires the Files.Read.All / Sites.Read.All scopes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword to search for (e.g. the meeting subject)."},
                    "count": {"type": "integer", "description": "Max files to return (default 15)", "default": 15},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="read_meeting_file",
            description=(
                "Download and return the text of a transcript file found via "
                "find_meeting_files. Works for .vtt transcripts (returned as readable "
                "'Speaker: text' lines). Pass the drive_id and item_id from "
                "find_meeting_files. Note: video recordings (.mp4) cannot be transcribed "
                "here — pick a .vtt/.txt/.docx transcript file if one is listed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "drive_id": {"type": "string", "description": "Drive ID from find_meeting_files."},
                    "item_id": {"type": "string", "description": "Item ID from find_meeting_files."},
                },
                "required": ["drive_id", "item_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
    except httpx.HTTPStatusError as e:
        result = _error(str(e), e.response.status_code)
    except Exception as e:
        result = _error(str(e))
    return [TextContent(type="text", text=result)]


async def _dispatch(name: str, args: dict) -> str:
    if name == "list_emails":
        return await _list_emails(args)
    elif name == "get_email":
        return await _get_email(args)
    elif name == "search_emails":
        return await _search_emails(args)
    elif name == "list_calendar_events":
        return await _list_calendar_events(args)
    elif name == "get_unread_emails":
        return await _get_unread_emails(args)
    elif name == "mark_email_read":
        return await _mark_email_read(args)
    elif name == "get_my_profile":
        return await _get_my_profile(args)
    elif name == "get_meeting_transcript":
        return await _get_meeting_transcript(args)
    elif name == "find_meeting_files":
        return await _find_meeting_files(args)
    elif name == "read_meeting_file":
        return await _read_meeting_file(args)
    else:
        return _error(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _list_emails(args: dict) -> str:
    count = int(args.get("count", 20))
    folder = args.get("folder", "inbox")
    search = args.get("search", "")

    select = "id,subject,from,receivedDateTime,bodyPreview,isRead"
    params: dict = {"$top": count, "$select": select, "$orderby": "receivedDateTime desc"}

    if search:
        params["$search"] = f'"{search}"'
        # $orderby cannot be combined with $search in Graph API
        del params["$orderby"]

    path = f"/me/mailFolders/{folder}/messages"
    resp = await _graph_request("GET", path, params=params)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    messages = resp.json().get("value", [])
    if not messages:
        return f"No emails found in {folder}."

    lines = [f"Emails in {folder} ({len(messages)} shown):"]
    for msg in messages:
        lines.append(_fmt_email(msg))

    return "\n".join(lines)


async def _get_email(args: dict) -> str:
    message_id = args["message_id"]
    select = "id,subject,from,toRecipients,receivedDateTime,body,isRead"
    resp = await _graph_request("GET", f"/me/messages/{message_id}", params={"$select": select})
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    msg = resp.json()

    # Format To: recipients
    to_recipients = msg.get("toRecipients", [])
    to_strs = [
        f"{r.get('emailAddress', {}).get('name', '')} <{r.get('emailAddress', {}).get('address', '')}>".strip()
        for r in to_recipients
    ]

    header = _fmt_email(msg, full_body=True)
    to_line = f"To:       {', '.join(to_strs)}" if to_strs else ""
    if to_line:
        # Insert To: line after From: line
        lines = header.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("Subject:"):
                lines.insert(i, to_line)
                break
        return "\n".join(lines)
    return header


async def _search_emails(args: dict) -> str:
    query = args["query"]
    count = int(args.get("count", 10))

    select = "id,subject,from,receivedDateTime,bodyPreview,isRead"
    params = {
        "$search": f'"{query}"',
        "$top": count,
        "$select": select,
    }

    resp = await _graph_request("GET", "/me/messages", params=params)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    messages = resp.json().get("value", [])
    if not messages:
        return f"No emails found matching '{query}'."

    lines = [f"Email search results for '{query}' ({len(messages)} found):"]
    for msg in messages:
        lines.append(_fmt_email(msg))

    return "\n".join(lines)


async def _list_calendar_events(args: dict) -> str:
    days_ahead = int(args.get("days_ahead", 7))
    days_back = int(args.get("days_back", 7))

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days_back)
    end = now + timedelta(days=days_ahead)

    start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    select = "id,subject,start,end,location,organizer,attendees,isOnlineMeeting,onlineMeeting,bodyPreview"
    params = {
        "startDateTime": start_str,
        "endDateTime": end_str,
        "$select": select,
        "$orderby": "start/dateTime asc",
        "$top": 50,
    }

    resp = await _graph_request("GET", "/me/calendarView", params=params)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    events = resp.json().get("value", [])
    if not events:
        return f"No calendar events from {days_back} day(s) ago through the next {days_ahead} days."

    lines = [f"Calendar events (last {days_back} day(s) → next {days_ahead} days, {len(events)} total):"]
    for event in events:
        lines.append(_fmt_event(event))

    return "\n".join(lines)


async def _get_unread_emails(args: dict) -> str:
    count = int(args.get("count", 10))

    select = "id,subject,from,receivedDateTime,bodyPreview,isRead"
    params = {
        "$filter": "isRead eq false",
        "$top": count,
        "$select": select,
        "$orderby": "receivedDateTime desc",
    }

    resp = await _graph_request("GET", "/me/messages", params=params)
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    messages = resp.json().get("value", [])
    if not messages:
        return "No unread emails found."

    lines = [f"Unread emails ({len(messages)} shown):"]
    for msg in messages:
        lines.append(_fmt_email(msg))

    return "\n".join(lines)


async def _mark_email_read(args: dict) -> str:
    message_id = args["message_id"]
    resp = await _graph_request(
        "PATCH",
        f"/me/messages/{message_id}",
        json_body={"isRead": True},
    )
    if resp.status_code not in (200, 204):
        return _error(resp.text, resp.status_code)

    return f"Email {message_id} marked as read."


def _clean_vtt(vtt: str) -> str:
    """Reduce a WebVTT transcript to readable 'Speaker: text' lines."""
    import re
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


def _meeting_id_from_join_url(join_url: str):
    """Construct the Graph onlineMeeting id straight from a Teams join URL.

    The id is base64('1*{organizerOid}*0**{threadId}'), where both parts are in
    the join URL. This lets an ATTENDEE read a meeting they did NOT organize —
    delegated OnlineMeetingTranscript.Read.All governs access — bypassing the
    organizer-only /me/onlineMeetings?$filter=JoinWebUrl lookup. For a recurring
    series (same join URL every week) this id returns every occurrence's transcript.
    """
    import base64
    from urllib.parse import unquote, urlparse
    try:
        p = urlparse(join_url)
        thread = unquote(p.path.split("/meetup-join/", 1)[1].split("/", 1)[0])  # 19:meeting_...@thread.v2
        ctx = json.loads(unquote(p.query.split("context=", 1)[1]))
        oid = ctx["Oid"]
        return base64.b64encode(f"1*{oid}*0**{thread}".encode()).decode()
    except Exception:
        return None


async def _resolve_join_url(event_id: str, join_url: str):
    """Return (join_url, error_str) from an explicit join URL or a calendar event."""
    join = (join_url or "").strip()
    if not join and event_id:
        r = await _graph_request(
            "GET", f"/me/events/{event_id}",
            params={"$select": "onlineMeeting,isOnlineMeeting,subject"},
        )
        if r.status_code != 200:
            return None, _error(r.text, r.status_code)
        join = ((r.json().get("onlineMeeting") or {}).get("joinUrl") or "").strip()
    if not join:
        return None, _error("That event has no Teams join URL — it may not be an online meeting.")
    return join, None


async def _get_meeting_transcript(args: dict) -> str:
    from urllib.parse import quote

    join, err = await _resolve_join_url(args.get("event_id", ""), args.get("join_url", ""))
    if err:
        return err
    mid = _meeting_id_from_join_url(join)
    if not mid:
        return _error("Could not parse the Teams join URL into a meeting id.")
    q = quote(mid, safe="")

    r = await _graph_request("GET", f"/me/onlineMeetings/{q}/transcripts")
    if r.status_code != 200:
        return _error(r.text, r.status_code)
    transcripts = r.json().get("value", [])
    if not transcripts:
        return "No transcript available for this meeting (transcription may have been off, or it's still processing)."
    transcripts.sort(key=lambda t: t.get("createdDateTime", ""), reverse=True)

    # Optionally pick a specific occurrence by date (YYYY-MM-DD); default = latest.
    on_date = (args.get("on_date") or "").strip()[:10]
    chosen = transcripts[0]
    if on_date:
        match = [t for t in transcripts if (t.get("createdDateTime", "")[:10] == on_date)]
        if not match:
            dates = ", ".join(sorted({t.get("createdDateTime", "")[:10] for t in transcripts}, reverse=True))
            return f"No transcript for {on_date}. Available occurrence dates: {dates}"
        chosen = match[0]

    tid = chosen["id"]
    c = await _graph_request(
        "GET", f"/me/onlineMeetings/{q}/transcripts/{quote(tid, safe='')}/content",
        params={"$format": "text/vtt"},
    )
    if c.status_code != 200:
        return _error(c.text, c.status_code)
    text = _clean_vtt(c.text)
    if not text:
        return "The transcript was empty after parsing."
    dates = ", ".join(sorted({t.get("createdDateTime", "")[:10] for t in transcripts}, reverse=True))
    header = (
        f"Meeting transcript for {chosen.get('createdDateTime','')[:10]} "
        f"({len(transcripts)} occurrence(s) available: {dates}):\n"
    )
    return header + text[:40000] + ("\n\n[... transcript truncated ...]" if len(text) > 40000 else "")


def _extract_docx_text(data: bytes) -> str:
    """Pull readable text out of a .docx (a zip containing word/document.xml)."""
    import io
    import zipfile
    import re
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    except Exception:
        return ""
    xml = re.sub(r"</w:p>", "\n", xml)          # paragraph breaks -> newlines
    text = re.sub(r"<[^>]+>", "", xml)           # strip all tags
    return re.sub(r"\n{3,}", "\n\n", text).strip()


async def _find_meeting_files(args: dict) -> str:
    query = args["query"].strip()
    count = int(args.get("count", 15))
    q_esc = query.replace("'", "''")
    results: list[dict] = []

    # 1) Search the user's own OneDrive
    r = await _graph_request(
        "GET", f"/me/drive/root/search(q='{q_esc}')",
        params={"$top": count,
                "$select": "id,name,webUrl,lastModifiedDateTime,parentReference,file,folder"},
    )
    if r.status_code in (401, 403):
        return _error(
            "Insufficient permissions to search files. The token needs the "
            "Files.Read.All (and Sites.Read.All) scope — add it to the app "
            "registration, get admin consent, and re-mint the token.", r.status_code)
    if r.status_code == 200:
        for it in r.json().get("value", []):
            if it.get("folder"):
                continue
            pr = it.get("parentReference", {})
            results.append({
                "name": it.get("name", ""),
                "drive_id": pr.get("driveId", ""),
                "item_id": it.get("id", ""),
                "modified": it.get("lastModifiedDateTime", ""),
                "source": "My OneDrive",
            })

    # 2) Files shared with the user (covers meetings organized by others)
    r2 = await _graph_request("GET", "/me/drive/sharedWithMe")
    if r2.status_code == 200:
        ql = query.lower()
        for it in r2.json().get("value", []):
            name = it.get("name", "")
            if ql and ql not in name.lower():
                continue
            remote = it.get("remoteItem", {})
            if remote.get("folder"):
                continue
            pr = remote.get("parentReference", {})
            results.append({
                "name": name,
                "drive_id": pr.get("driveId", ""),
                "item_id": remote.get("id", ""),
                "modified": remote.get("lastModifiedDateTime", ""),
                "source": "Shared with me",
            })

    seen: set = set()
    lines = [f"Files matching '{query}':"]
    found = 0
    for f in results:
        key = (f["drive_id"], f["item_id"])
        if not f["item_id"] or key in seen:
            continue
        seen.add(key)
        found += 1
        lines.append(
            f"\n• {f['name']}  [{f['source']}]"
            f"\n    drive_id: {f['drive_id']}"
            f"\n    item_id:  {f['item_id']}"
            f"\n    modified: {_fmt_datetime(f['modified'])}"
        )
    if not found:
        return f"No files found matching '{query}' in your OneDrive or shared files."
    lines.insert(1, f"({found} found)")
    lines.append("\nTo read a transcript, call read_meeting_file with a .vtt/.txt/.docx file's drive_id + item_id.")
    return "\n".join(lines)


async def _read_meeting_file(args: dict) -> str:
    drive_id = args["drive_id"]
    item_id = args["item_id"]

    meta = await _graph_request(
        "GET", f"/drives/{drive_id}/items/{item_id}", params={"$select": "name,file"})
    if meta.status_code in (401, 403):
        return _error(
            "Insufficient permissions to read files. The token needs the "
            "Files.Read.All (and Sites.Read.All) scope.", meta.status_code)
    if meta.status_code != 200:
        return _error(meta.text, meta.status_code)
    name = meta.json().get("name", "")
    lname = name.lower()

    if lname.endswith((".mp4", ".mov", ".m4a", ".wav", ".mp3")):
        return (f"'{name}' is a media recording, not a text transcript — I can't transcribe "
                f"audio/video here. Look for a .vtt/.txt/.docx transcript file for this meeting.")

    c = await _graph_request("GET", f"/drives/{drive_id}/items/{item_id}/content")
    if c.status_code not in (200, 206):
        return _error(c.text, c.status_code)
    raw = c.content

    if lname.endswith(".vtt"):
        text = _clean_vtt(raw.decode("utf-8", errors="replace"))
    elif lname.endswith((".txt", ".csv")):
        text = raw.decode("utf-8", errors="replace").strip()
    elif lname.endswith(".docx"):
        text = _extract_docx_text(raw)
    else:
        text = raw.decode("utf-8", errors="replace").strip()
        if not text or "\x00" in text[:200]:
            return (f"'{name}' doesn't look like a readable text transcript "
                    f"(unrecognized/binary format). Pick a .vtt/.txt/.docx file instead.")

    if not text:
        return f"'{name}' was empty after parsing."
    header = f"Transcript from '{name}':\n"
    return header + text[:15000] + ("\n\n[... truncated ...]" if len(text) > 15000 else "")


async def _get_my_profile(args: dict) -> str:
    resp = await _graph_request("GET", "/me")
    if resp.status_code != 200:
        return _error(resp.text, resp.status_code)

    profile = resp.json()
    lines = [
        "M365 User Profile:",
        f"  Name:          {profile.get('displayName', '')}",
        f"  Email:         {profile.get('mail') or profile.get('userPrincipalName', '')}",
        f"  Job Title:     {profile.get('jobTitle') or '—'}",
        f"  Department:    {profile.get('department') or '—'}",
        f"  Office:        {profile.get('officeLocation') or '—'}",
        f"  Phone:         {profile.get('mobilePhone') or profile.get('businessPhones', ['—'])[0]}",
        f"  ID:            {profile.get('id', '')}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main():
    if not CLIENT_ID:
        print(
            "ERROR: M365_CLIENT_ID is not set. Copy .env.example to .env and fill in your Azure app credentials.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("M365 MCP server ready", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
