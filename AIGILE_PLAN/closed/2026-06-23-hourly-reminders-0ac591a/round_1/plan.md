## Burst Plan

**Goal:** Deliver an hourly reminder system that creates a notification for a task's assignee every hour until the task is completed or unassigned, with a backend scheduler, a notifications read API, and a frontend notification surface.

**CHARTER alignment:** Advances "Complete backend API — all routers functional" (adds the missing notifications router) and "Frontend connected to live backend — no mock data" (adds a live notification surface). Honours Hard Spec "All schema changes via numbered migration files."

**Streams:** Three streams, sequenced then partially parallel. Stream A (backend foundation: migration + model + Notification schema + notifications router) is a hard prerequisite. Streams B (scheduler) and C (frontend) both depend on A and are pairwise file-disjoint, so B and C run in parallel after A merges.

### Stream A - Notifications foundation (schema, model, read API)

- Scope:
  - `database/001_task_reminders.sql` (NEW numbered migration — starts the numbered series at `001_`; existing files (`schema.sql`/`seed.sql`/`pgvector_setup.sql`) stay unnumbered and are NOT renamed since they are already applied; idempotent `ALTER TABLE tasks ADD COLUMN IF NOT EXISTS last_reminded_at TIMESTAMPTZ`, plus index `idx_tasks_reminder ON tasks (assigned_to, is_completed) WHERE assigned_to IS NOT NULL AND is_completed = FALSE`)
  - `database/schema.sql` (add the same `last_reminded_at` column to the canonical `tasks` table definition at lines 129-144 to keep bootstrap in sync, per the global "bootstrap.sql must stay in sync" rule)
  - `backend/app/models/models.py` (add `last_reminded_at: Mapped[Optional[datetime]]` to `Task`; add a Python `EntityType` Enum class and change `Notification.entity_type` from `String(50)` to `SQLAlchemyEnum(EntityType, ...)` so the ORM mapping matches the PostgreSQL `entity_type` enum column defined in `schema.sql`; the rest of the `Notification` model at lines 203-216 already has `user_id`, `type`, `title`, `body`, `entity_type`, `entity_id`, `is_read`, `created_at` — no further change needed)
  - `backend/app/schemas/schemas.py` (NEW `NotificationOut` schema; verify it mirrors the existing `from_attributes` pattern used by `TaskOut`; add `last_reminded_at` to `TaskOut` only if the Orchestrator wants it surfaced — otherwise exclude)
  - `backend/app/api/v1/notifications.py` (NEW router, prefix `/notifications`, mirroring `tasks.py` structure: `GET /` list current user's notifications (defaults to last 20, unread-first ordering, newest-first; supports `?limit=N` and `?unread=true` query parameters), `PATCH /{id}/read` mark read, `POST /{id}/read-all` or `PATCH /read-all` mark all read; all gated by `get_current_user` from `app.core.deps`, and all single-notification mutations constrain by both notification id AND `user_id = current_user.id`)
  - `backend/app/main.py` (register the new router: add `notifications` to the `from app.api.v1 import ...` line 7 and add `app.include_router(notifications.router, prefix=PREFIX)` after the existing includes, lines 28-34)
- Excluded: scheduler code, `requirements.txt`, all frontend files
- Exports (interface contract):
  - `Notification` ORM with `entity_type` mapped via `SQLAlchemyEnum(EntityType)`; `Task.last_reminded_at` column available
  - REST: `GET /api/v1/notifications` -> `List[NotificationOut]` (fields: `id`, `user_id`, `type`, `title`, `body`, `entity_type`, `entity_id`, `is_read`, `created_at`; defaults to last 20 unread-first/newest-first, accepts `?limit=N&unread=true`), `PATCH /api/v1/notifications/{id}/read` (ownership-scoped by `user_id = current_user.id`), `PATCH /api/v1/notifications/read-all`
  - Reminder notification convention: `type="reminder"`, `entity_type="task"`, `entity_id=<task.id>` (note PG `entity_type` is an ENUM that already includes `'task'`)
- Dependency: none (foundation)
- Builder: claude

### Stream B - Hourly reminder scheduler

- Scope:
  - `backend/requirements.txt` (REMOVE APScheduler from scope; add `pytest`, `pytest-asyncio`, `httpx` for the integration tests)
  - `backend/app/services/reminder_service.py` (NEW — the core job: open an `AsyncSessionLocal` from `app.db.session`, select tasks where `assigned_to IS NOT NULL AND is_completed = FALSE AND (last_reminded_at IS NULL OR last_reminded_at < now() - interval '1 hour')`, and for each eligible task insert a `Notification` and stamp `Task.last_reminded_at`; reuse the `select`/`async with` patterns already in `tasks.py` and `deps.py`. The one-hour threshold is part of the core query contract, not just the case enumeration)
  - `backend/app/api/v1/internal.py` (NEW — `POST /api/v1/internal/run-reminders` endpoint gated by a `CRON_SECRET` env var; calls `run_task_reminders(session)`. Replaces the in-process APScheduler approach: Railway Cron Service triggers this endpoint hourly. Register this router in `main.py` — Stream A owns the `main.py` router-include edits, so coordinate the single internal-router include line with Stream A's foundation merge)
  - `backend/tests/test_reminders.py` (NEW — integration tests covering the four scheduler cases: eligible, completed, unassigned, inactive-user; uses `pytest`/`pytest-asyncio`/`httpx`)
  - `railway.json` (NEW — documents the Railway Cron Service setup that triggers `POST /api/v1/internal/run-reminders` hourly with the `CRON_SECRET`)
- Excluded: notifications router, schemas, models migration (consumes A's column), all frontend files
- Exports (interface contract):
  - `run_task_reminders(session)` service function (testable in isolation)
  - `POST /api/v1/internal/run-reminders` internal endpoint (gated by `CRON_SECRET`), triggered by Railway Cron
- Case enumeration (scheduler job state machine — MANDATORY):
  - Happy path: task assigned, not completed, `last_reminded_at` older than ~1h (or null) -> create one reminder notification, update `last_reminded_at`
  - Empty/missing input: no eligible tasks -> job no-ops, no error
  - Malformed/orphaned: `assigned_to` points to a deleted/inactive user -> skip (the FK is `ON DELETE SET NULL`, so assigned_to becomes null and is filtered out; also guard against inactive users)
  - Partial/intermediate state: task just completed or unassigned between job runs -> excluded by the `is_completed=FALSE AND assigned_to IS NOT NULL` filter; no reminder
  - Missing dependency: DB unreachable mid-job -> catch, log, do not crash; duplicate-run guard via `last_reminded_at` threshold in the core query so a re-trigger within the hour does not double-send. Multi-worker overlap is avoided by construction: Railway Cron triggers a single endpoint invocation rather than running an in-process scheduler in every worker.
- Dependency: Stream A (needs `Task.last_reminded_at` column and the agreed `Notification` reminder convention)
- Builder: claude

### Stream C - Frontend notification surface

- Scope:
  - `frontend/lib/api.ts` (NEW `notificationsApi` block: `list()`, `markRead(id)`, `markAllRead()`, mirroring the existing `tasksApi`/`projectsApi` axios pattern at lines 55-63)
  - `frontend/lib/types.ts` (NEW `Notification` TS interface matching `NotificationOut`)
  - `frontend/components/layout/NotificationBell.tsx` (NEW — bell with unread count, dropdown listing reminders, mark-read action; client component, polls `notificationsApi.list()` on an interval)
  - `frontend/app/(dashboard)/layout.tsx` (mount `<NotificationBell />` unconditionally so the bell is global across all dashboard pages, rather than in the conditional Header actions area)
- Excluded: all backend files, all other frontend pages
- Exports: visual notification bell + dropdown wired to the live `/notifications` API
- Dependency: Stream A (consumes `GET /api/v1/notifications` and `NotificationOut` shape)
- Builder: claude

**Shared files:**
- `backend/app/main.py` — Stream A owns all router-include edits (notifications router for Stream A, plus the internal router line on Stream B's behalf). Stream B no longer adds any lifespan/scheduler hook, so `main.py` is not a concurrent-writer coordination point: Stream A lands the foundation merge including both router includes.
- `frontend/app/(dashboard)/layout.tsx` — written only by Stream C (not shared).

**Integration gate:**
- Stream A merges first. Verify: `uvicorn app.main:app` boots, `GET /api/v1/notifications` returns 200 with bearer token, migration `001_task_reminders.sql` applies idempotently against a fresh DB and re-runs cleanly (IF NOT EXISTS), `schema.sql` tasks table matches the migration. Verify `GET /notifications?limit=N&unread=true` returns the bounded, unread-first, newest-first list. Verify a cross-user `PATCH /notifications/{id}/read` against another user's notification returns 403 (ownership guard).
- Streams B and C merge after A. B's internal-router include line rebases on A's merged `main.py`.
- Probe acceptance: assign a task to a user -> within the configured interval a `type="reminder"` notification row appears for that user and shows in the frontend bell; complete or unassign the task -> no further reminders; re-trigger the internal endpoint within the hour -> no duplicate reminder (last_reminded_at guard). Integration test covering the four scheduler cases above (eligible, completed, unassigned, inactive-user) must pass under pytest (`pytest`/`pytest-asyncio`/`httpx`).

**Deferred to next Burst:**
- Real-time push (WebSocket/SSE) for instant bell updates — v0 uses frontend polling.
- Email/Slack delivery of reminders — v0 is in-app notifications only.
- Per-user reminder cadence configuration and quiet hours.

### Critical Files for Implementation
- backend/app/main.py
- backend/app/models/models.py
- database/schema.sql
- backend/app/api/v1/tasks.py
- frontend/lib/api.ts
