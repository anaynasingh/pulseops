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
from app.api.v1 import auth, projects, tasks, kanban, ai, search, analytics, users


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
    app.mount("/mcp", SSEKeepAliveMiddleware(mcp.sse_app()))
    import logging
    logging.getLogger(__name__).info("MCP server mounted at /mcp (SSE + keep-alive)")
except Exception as e:
    import logging
    logging.getLogger(__name__).error(f"MCP server failed to mount: {e}")
