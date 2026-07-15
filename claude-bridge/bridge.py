"""
PulseOps — Claude Code Bridge

A tiny local HTTP service that connects the PulseOps AI Assistant chatbot to
the Claude Code CLI installed on this machine.

Flow:
  PulseOps chat panel → backend POST /api/v1/ai/claude-chat → this bridge
  → `claude -p` (headless, with the PulseOps MCP tools) → reply → chat panel

Claude gets the PulseOps MCP server, so it can list projects, read meeting
transcripts, create tasks on the Kanban board, move projects, etc.

Run:
  cd claude-bridge
  pip install -r requirements.txt
  copy .env.example .env   (fill in your PulseOps login)
  python bridge.py
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

BRIDGE_DIR = Path(__file__).resolve().parent
load_dotenv(BRIDGE_DIR / ".env")

REPO_ROOT = BRIDGE_DIR.parent
PULSEOPS_MCP_SERVER = REPO_ROOT / "mcp-servers" / "pulseops" / "server.py"
M365_MCP_SERVER = REPO_ROOT / "mcp-servers" / "m365" / "server.py"
MCP_CONFIG_PATH = BRIDGE_DIR / ".mcp-config.json"   # generated at startup (gitignored)
WORKDIR = BRIDGE_DIR / "workdir"                    # neutral cwd so no project CLAUDE.md is loaded

# Railway (and most PaaS) inject the port to bind as $PORT; fall back to
# BRIDGE_PORT for local dev.
BRIDGE_PORT = int(os.getenv("PORT") or os.getenv("BRIDGE_PORT", "8765"))
# Host to bind. Locally 127.0.0.1 keeps the bridge off the network; on Railway
# it must be 0.0.0.0 so the private network can reach it (set BRIDGE_HOST there).
BRIDGE_HOST = os.getenv("BRIDGE_HOST", "127.0.0.1")
# Optional shared secret. When set, callers (the PulseOps backend) must send it
# as the X-Bridge-Secret header. Leave empty for local dev.
BRIDGE_SECRET = os.getenv("BRIDGE_SECRET", "").strip()
CLAUDE_TIMEOUT_SECONDS = int(os.getenv("CLAUDE_TIMEOUT_SECONDS", "540"))
MAX_TURNS = os.getenv("CLAUDE_MAX_TURNS", "40")
PYTHON_CMD = os.getenv("PYTHON_CMD", sys.executable or "python")

# M365 (Outlook mail/calendar + Teams transcripts) is attached only when an
# Azure app client id is configured. Kept optional so local/transcripts-only
# runs work unchanged.
M365_ENABLED = bool(os.getenv("M365_CLIENT_ID", "").strip())
ALLOWED_TOOLS = "mcp__pulseops,mcp__m365" if M365_ENABLED else "mcp__pulseops"

SYSTEM_PROMPT = """You are the PulseOps AI Assistant, powered by Claude Code and embedded in the
PulseOps team task-management app. Your reply text is shown directly in a small chat panel.

You have PulseOps MCP tools to act on the user's real workspace:
- list_projects / get_project / create_project / update_project / move_project
- create_task / update_task
- list_transcripts / get_transcript / analyze_transcript  (meeting transcripts)
- get_dashboard / search_projects / get_gantt / process_email

Rules:
- When the user asks you to do something (e.g. "read meeting transcripts and create tasks"),
  actually do it with the tools — don't just describe how.
- Tasks must belong to a project: find a fitting existing project with list_projects/search_projects
  first; only create a new project if nothing fits.
- Before creating tasks, check existing ones in the target project to avoid duplicates.
- Always hard-assign tasks to the right person: pass the `assignee` field on create_task / update_task using their EMAIL (e.g. first.last@prospect33.com — most reliable; a full name also works). Do NOT put the owner's name in the task title — the assignee field is what records ownership. If you can't map an owner to a user, say so rather than guessing.
- Keep replies short and chat-friendly: what you did, what you found, and any IDs/links that help.
  Use simple markdown (bold, bullet lists). No headings, no code blocks unless asked.
- Stay on topic: projects, tasks, meetings, priorities, team workload. Politely decline anything else.
"""

# Appended only when the M365 server is attached.
M365_PROMPT = """

You also have Microsoft 365 tools for the signed-in user's own account:
- list_calendar_events (find meetings), get_meeting_transcript (read a Teams meeting transcript by event id or join URL)
- list_emails / search_emails / get_email / get_unread_emails (read Outlook mail), get_my_profile

Turning a meeting into tasks: call list_calendar_events to find the meeting, then get_meeting_transcript with that event's id, read/summarize it, and create tasks on the board with the PulseOps tools. If a transcript isn't available (transcription was off, still processing, or you weren't the organizer), say so plainly and offer to work from pasted text instead. Do the same for emails: read with the M365 tools, then create tasks with PulseOps."""


# ---------------------------------------------------------------------------
# Claude CLI discovery
# ---------------------------------------------------------------------------

def find_claude_cli() -> list[str]:
    """Return the command prefix to invoke the Claude Code CLI.

    Avoids npm's .cmd shim: cmd.exe mangles arguments containing '&'
    (this repo's folder name has one), so resolve the real executable.
    """
    override = os.getenv("CLAUDE_CLI_PATH")
    if override:
        return [override]

    # 1. Native exe inside the global npm install (what claude.cmd points at)
    appdata = os.getenv("APPDATA", "")
    npm_exe = Path(appdata) / "npm" / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    if npm_exe.exists():
        return [str(npm_exe)]

    # 2. cli.js run through node (also bypasses cmd.exe)
    npm_cli_js = Path(appdata) / "npm" / "node_modules" / "@anthropic-ai" / "claude-code" / "cli.js"
    node = shutil.which("node")
    if npm_cli_js.exists() and node:
        return [node, str(npm_cli_js)]

    # 3. Whatever is on PATH (fine on macOS/Linux and for native installs)
    for name in ("claude.exe", "claude"):
        path = shutil.which(name)
        if path and not path.lower().endswith((".ps1", ".cmd")):
            return [path]
    cmd_shim = shutil.which("claude.cmd") or shutil.which("claude")
    if cmd_shim:
        return [cmd_shim]

    raise RuntimeError(
        "Claude Code CLI not found on PATH. Install it (npm install -g @anthropic-ai/claude-code) "
        "or set CLAUDE_CLI_PATH in claude-bridge/.env"
    )


def write_mcp_config() -> None:
    """Generate the MCP config Claude will use, from this bridge's .env."""
    api_key = os.getenv("PULSEOPS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "PULSEOPS_API_KEY not set. Copy .env.example to .env and paste your personal "
            "MCP token from PulseOps (shown in the Claude setup modal in the sidebar)."
        )
    config = {
        "mcpServers": {
            "pulseops": {
                "command": PYTHON_CMD,
                "args": [str(PULSEOPS_MCP_SERVER)],
                "env": {
                    "PULSEOPS_API_URL": os.getenv("PULSEOPS_API_URL", "http://localhost:8001/api/v1"),
                    "PULSEOPS_API_KEY": api_key,
                },
            }
        }
    }

    if M365_ENABLED:
        # Pass only the vars that are actually set so the server can fall back to
        # its own defaults; force NO_DEVICE_FLOW so a missing token fails fast
        # instead of hanging on an interactive login nobody can complete.
        m365_env = {
            "M365_CLIENT_ID": os.getenv("M365_CLIENT_ID", ""),
            "M365_TENANT_ID": os.getenv("M365_TENANT_ID", "common"),
            "M365_NO_DEVICE_FLOW": "1",
        }
        for passthru in ("M365_TOKEN_CACHE", "M365_TOKEN_B64", "M365_SCOPES", "M365_CLIENT_SECRET"):
            val = os.getenv(passthru, "").strip()
            if val:
                m365_env[passthru] = val
        config["mcpServers"]["m365"] = {
            "command": PYTHON_CMD,
            "args": [str(M365_MCP_SERVER)],
            "env": m365_env,
        }

    MCP_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

app = FastAPI(title="PulseOps Claude Bridge")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None   # Claude session id from a previous reply
    user_email: Optional[str] = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "pulseops-claude-bridge"}


@app.post("/chat")
def chat(
    payload: ChatRequest,
    x_bridge_secret: Optional[str] = Header(default=None),
) -> dict:
    """Run one chat turn through Claude Code headless mode.

    When BRIDGE_SECRET is configured (e.g. on Railway), the caller must present
    it in the X-Bridge-Secret header. This is the only auth on the endpoint, so
    the bridge should also be kept on a private network.
    """
    if BRIDGE_SECRET and x_bridge_secret != BRIDGE_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing bridge secret.")
    return _do_chat(payload)


def _do_chat(payload: ChatRequest) -> dict:
    """Execute one Claude turn. Split from the endpoint so the resume-retry can
    recurse without re-checking the (already-verified) shared secret."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    system_prompt = SYSTEM_PROMPT + (M365_PROMPT if M365_ENABLED else "")
    if payload.user_email:
        system_prompt += f"\nThe user chatting with you is logged in as: {payload.user_email}"

    cmd = list(CLAUDE_CMD) + [
        "-p",
        "--output-format", "json",
        "--mcp-config", str(MCP_CONFIG_PATH),
        "--strict-mcp-config",
        # dontAsk = auto-approve only the pre-approved tools below and deny the
        # rest. REQUIRED in headless mode: without it, an MCP permission prompt
        # has no one to answer and aborts the run (fine on a dev machine that
        # already trusts the tools, but fatal in a fresh container).
        "--permission-mode", "dontAsk",
        "--allowedTools", ALLOWED_TOOLS,
        "--disallowedTools", "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch,Task",
        "--append-system-prompt", system_prompt,
        "--max-turns", MAX_TURNS,
    ]
    if payload.session_id:
        cmd += ["--resume", payload.session_id]
    cmd.append(payload.message)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(WORKDIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=CLAUDE_TIMEOUT_SECONDS,
            env=env,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Claude timed out on this request.")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Claude CLI not found. Check CLAUDE_CLI_PATH.")

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or proc.stdout or "").strip()[-500:]
        # A stale/unknown session id makes --resume fail; retry once fresh.
        if payload.session_id:
            retry = ChatRequest(message=payload.message, user_email=payload.user_email)
            return _do_chat(retry)
        raise HTTPException(status_code=502, detail=f"Claude CLI failed: {stderr_tail}")

    try:
        result = json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        # Fall back to raw text if the CLI printed something unexpected
        return {"reply": proc.stdout.strip()[:4000], "session_id": None, "engine": "claude-code"}

    reply = result.get("result") or "Claude finished but returned no text."
    return {
        "reply": reply,
        "session_id": result.get("session_id"),
        "engine": "claude-code",
        "is_error": bool(result.get("is_error")),
        "duration_ms": result.get("duration_ms"),
        "num_turns": result.get("num_turns"),
    }


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

CLAUDE_CMD = find_claude_cli()

if __name__ == "__main__":
    import uvicorn

    WORKDIR.mkdir(exist_ok=True)
    write_mcp_config()
    print(f"PulseOps Claude Bridge ready on http://{BRIDGE_HOST}:{BRIDGE_PORT}")
    print(f"  Claude CLI : {' '.join(CLAUDE_CMD)}")
    print(f"  MCP server : {PULSEOPS_MCP_SERVER}")
    print(f"  Auth       : {'shared secret required' if BRIDGE_SECRET else 'OPEN (no secret set)'}")

    if BRIDGE_HOST == "::":
        # Bind an explicit DUAL-STACK IPv6 socket. Railway's private network is
        # IPv6 (needs ::), but its public edge + healthchecks probe over IPv4.
        # This container defaults to IPV6_V6ONLY=1, so a plain "::" bind is
        # IPv6-only and unreachable from IPv4. Clearing V6ONLY makes one socket
        # serve both.
        import socket
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError) as exc:
            print(f"  (warning: could not enable dual-stack: {exc})")
        sock.bind(("::", BRIDGE_PORT))
        uvicorn.Server(uvicorn.Config(app, log_level="info")).run(sockets=[sock])
    else:
        uvicorn.run(app, host=BRIDGE_HOST, port=BRIDGE_PORT)
