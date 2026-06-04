# Orchestrator redirects: hourly-reminders

## 2026-06-03T09:41:03Z | round_0 | scope-change

**Round:** 0 (plan phase, pre-build)
**Classification:** Scope/architecture redirect
**What changed:** Stream B redesigned — APScheduler (in-process) replaced by Railway Cron Service pattern. Orchestrator confirmed app deploys to Railway; in-process scheduler breaks on multi-worker scale.
**Effect:** `backend/app/core/scheduler.py` and APScheduler dependency removed. Replace with Railway Cron + internal endpoint `POST /api/v1/internal/run-reminders` (CRON_SECRET gated). `main.py` lifespan hook not needed for scheduler.
