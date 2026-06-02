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
SCOPES = ["Mail.Read", "Calendars.Read", "Mail.ReadWrite"]
TOKEN_CACHE_PATH = Path.home() / ".pulseops_m365_token.json"

# ---------------------------------------------------------------------------
# MSAL auth
# ---------------------------------------------------------------------------
_token_cache = msal.SerializableTokenCache()


def _load_cache() -> None:
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

    # Fall back to device code flow
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
            description="List upcoming calendar events from Outlook Calendar.",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "How many days ahead to look (default 7)", "default": 7},
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

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_ahead)

    start_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
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
        return f"No calendar events in the next {days_ahead} days."

    lines = [f"Upcoming calendar events (next {days_ahead} days, {len(events)} total):"]
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
