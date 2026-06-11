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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.api.v1 import auth, projects, tasks, kanban, ai, search, analytics, users

app = FastAPI(
    title="PulseOps API",
    description="AI-Powered Team Operations & Workflow Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    # Trust Railway's reverse proxy so redirects use https:// not http://
    root_path_in_servers=False,
)

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
    return {"status": "ok", "service": "PulseOps API", "version": "1.0.0"}


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
    app.mount("/mcp", mcp.sse_app())
    import logging
    logging.getLogger(__name__).info("MCP server mounted at /mcp (SSE transport)")
except Exception as e:
    import logging
    logging.getLogger(__name__).error(f"MCP server failed to mount: {e}")
