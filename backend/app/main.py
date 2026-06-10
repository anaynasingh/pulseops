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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth, projects, tasks, kanban, ai, search, analytics, users
from app.api.v1.mcp_server import mcp

app = FastAPI(
    title="PulseOps API",
    description="AI-Powered Team Operations & Workflow Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


# Mount MCP server — Claude connects via: claude mcp add task-planner <URL>/mcp
app.mount("/mcp", mcp.streamable_http_app())


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "PulseOps API", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "message": "PulseOps API — AI-Powered Team Operations Platform",
        "docs": "/docs",
    }
