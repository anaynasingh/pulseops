"""
PulseOps — FastAPI Application Entry Point
"""
# ── bcrypt/passlib compatibility patch ────────────────────────────────────────
# passlib 1.7.4 tries to read bcrypt.__about__.__version__ which doesn't exist
# in bcrypt 4.x+. Patch it before anything imports passlib.
try:
    import bcrypt as _bcrypt
    if not hasattr(_bcrypt, '__about__'):
        class _About:
            __version__ = getattr(_bcrypt, '__version__', '4.0.1')
        _bcrypt.__about__ = _About()
except Exception:
    pass
# ──────────────────────────────────────────────────────────────────────────────

import anyio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send
from app.core.config import settings
from app.api.v1 import auth, projects, tasks, kanban, ai, search, analytics, users, internal, proposed_tasks


class SSEKeepAliveMiddleware:
    """
    Sends SSE comment pings every INTERVAL seconds so Railway's proxy never
    kills idle SSE connections mid-handshake or mid-session.
    """
    def __init__(self, app: ASGIApp, interval: float = 20.0):
        self.app = app
        self.interval = interval

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or not scope.get("path", "").endswith("/sse"):
            await self.app(scope, receive, send)
            return

        lock = anyio.Lock()
        done = False

        async def safe_send(message):
            async with lock:
                await send(message)

        async def ping_loop(*, task_status=anyio.TASK_STATUS_IGNORED):
            task_status.started()
            while not done:
                await anyio.sleep(self.interval)
                if done:
                    break
                try:
                    async with lock:
                        await send({
                            "type": "http.response.body",
                            "body": b": ping\n\n",
                            "more_body": True,
                        })
                except Exception:
                    break

        async with anyio.create_task_group() as tg:
            await tg.start(ping_loop)
            await self.app(scope, receive, safe_send)
            done = True
            tg.cancel_scope.cancel()


class MCPHeaderMiddleware:
    """
    Pure ASGI middleware — reads X-Token header from the ASGI scope
    and stores it in a ContextVar before every request.
    Uses raw ASGI (not BaseHTTPMiddleware) so receive/send are never wrapped,
    avoiding body-buffering issues with ASGI-mounted sub-apps like FastMCP.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            from app.api.v1.mcp_server import mcp_token_var, mcp_email_var, mcp_password_var
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            token = headers.get(b"x-token", b"").decode() or None
            email = headers.get(b"x-email", b"").decode() or None
            password = headers.get(b"x-password", b"").decode() or None
            t_token = mcp_token_var.set(token)
            t_email = mcp_email_var.set(email)
            t_password = mcp_password_var.set(password)
            try:
                await self.app(scope, receive, send)
            finally:
                mcp_token_var.reset(t_token)
                mcp_email_var.reset(t_email)
                mcp_password_var.reset(t_password)
        else:
            await self.app(scope, receive, send)

app = FastAPI(
    title="PulseOps API",
    description="AI-Powered Team Operations & Workflow Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    # Trust Railway's reverse proxy so redirects use https:// not http://
    root_path_in_servers=False,
)


@app.on_event("startup")
async def run_migrations():
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS ms_oid TEXT"))
        await db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_ms_oid ON users (ms_oid) WHERE ms_oid IS NOT NULL"))
        await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS api_key TEXT"))
        await db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_api_key ON users (api_key) WHERE api_key IS NOT NULL"))
        await db.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ"))
        await db.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 60"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_at ON tasks (assigned_to, scheduled_at) WHERE scheduled_at IS NOT NULL"))
        await db.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS last_reminded_at TIMESTAMPTZ"))
        await db.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS block_reminded_at TIMESTAMPTZ"))
        await db.execute(text("ALTER TABLE request_intake ADD COLUMN IF NOT EXISTS suggested_item_type TEXT"))
        # 007_proposed_tasks.sql mirror (transcript intake bell) — keep byte-for-byte
        # in sync with database/007_proposed_tasks.sql. NOTE: the enum type is
        # priority_level (underscore) as defined in schema.sql.
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS proposed_tasks (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                transcript_id UUID REFERENCES meeting_transcripts(id) ON DELETE CASCADE,
                meeting_title TEXT,
                meeting_date DATE,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                priority priority_level DEFAULT 'medium',
                assignee_hint VARCHAR(255),
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_task_id UUID,
                dedup_status VARCHAR(20),
                dedup_existing_task_id UUID,
                proposed_at TIMESTAMPTZ DEFAULT now(),
                handled_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_proposed_tasks_user_status ON proposed_tasks (user_id, status)"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_proposed_tasks_transcript ON proposed_tasks (transcript_id)"))
        await db.execute(text("ALTER TABLE meeting_transcripts ADD COLUMN IF NOT EXISTS graph_transcript_id VARCHAR(255)"))
        await db.execute(text("ALTER TABLE meeting_transcripts ADD COLUMN IF NOT EXISTS graph_meeting_id VARCHAR(255)"))
        await db.execute(text("ALTER TABLE meeting_transcripts ADD COLUMN IF NOT EXISTS truncated BOOLEAN DEFAULT FALSE"))
        await db.execute(text("ALTER TABLE meeting_transcripts ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMPTZ"))
        await db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_meeting_transcripts_graph_transcript_id ON meeting_transcripts (graph_transcript_id) WHERE graph_transcript_id IS NOT NULL"))
        await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS m365_last_transcript_poll TIMESTAMPTZ"))
        await db.commit()


@app.on_event("startup")
async def start_transcript_poll_scheduler():
    """In-process transcript poll every ~10 min (single-process Railway deploy;
    replica scale-out via Railway Cron stays Deferred). max_instances=1 plus the
    shared poll_lock (R1-1) serialize the job against manual internal triggers."""
    import logging
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from app.services.transcript_poll_service import run_transcript_poll_locked

        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(
            run_transcript_poll_locked,
            "interval",
            minutes=10,
            max_instances=1,
            coalesce=True,
            id="transcript-poll",
        )
        scheduler.start()
        app.state.transcript_scheduler = scheduler
        logging.getLogger(__name__).info("Transcript poll scheduler started (every 10 min)")
    except Exception as e:
        logging.getLogger(__name__).error(f"Transcript poll scheduler failed to start: {e}")

# Capture MCP auth headers before every request (pure ASGI, not BaseHTTPMiddleware)
app.add_middleware(MCPHeaderMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(projects.router, prefix=PREFIX)
app.include_router(tasks.router, prefix=PREFIX)
app.include_router(kanban.router, prefix=PREFIX)
app.include_router(ai.router, prefix=PREFIX)
app.include_router(search.router, prefix=PREFIX)
app.include_router(analytics.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(internal.router, prefix=PREFIX)
app.include_router(proposed_tasks.router, prefix=PREFIX)


@app.get("/health")
async def health_check():
    import mcp as _mcp
    import mcp.types as _t
    return {
        "status": "ok",
        "service": "PulseOps API",
        "version": "1.0.0",
        "mcp_version": getattr(_mcp, "__version__", "unknown"),
        "mcp_protocol": getattr(_t, "LATEST_PROTOCOL_VERSION", "unknown"),
    }


@app.get("/")
async def root():
    return {
        "message": "PulseOps API — AI-Powered Team Operations Platform",
        "docs": "/docs",
    }


# Mount MCP server LAST so all FastAPI routes take priority.
# Using sse_app() which works correctly when embedded inside FastAPI.
# streamable_http_app() requires its own lifecycle (run()) and fails embedded.
try:
    from app.api.v1.mcp_server import mcp
    # FastMCP's sse_app() advertises its message endpoint to clients using
    # settings.message_path verbatim. Mounting the sub-app under "/mcp" does
    # NOT rewrite that path, so it stays the root-relative default
    # "/messages/". Clients then POST tool calls to /messages/ -> 404, the MCP
    # session never exchanges messages, and tools silently return nothing
    # ("no tasks"). Fix: bake the /mcp prefix into both paths and mount at root,
    # so the advertised endpoint matches the real handler (/mcp/messages/).
    # Client connection URL is unchanged (still .../mcp/sse).
    mcp.settings.sse_path = "/mcp/sse"
    mcp.settings.message_path = "/mcp/messages/"
    app.mount("/", SSEKeepAliveMiddleware(mcp.sse_app()))
    import logging
    logging.getLogger(__name__).info("MCP server mounted (SSE /mcp/sse + messages /mcp/messages/)")
except Exception as e:
    import logging
    logging.getLogger(__name__).error(f"MCP server failed to mount: {e}")
