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
- Keep replies short and chat-friendly: what you did, what you found, and any IDs/links that help.
  Use simple markdown (bold, bullet lists). No headings, no code blocks unless asked.
- Stay on topic: projects, tasks, meetings, priorities, team workload. Politely decline anything else.
"""


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

    system_prompt = SYSTEM_PROMPT
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
        "--allowedTools", "mcp__pulseops",
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
    uvicorn.run(app, host=BRIDGE_HOST, port=BRIDGE_PORT)
