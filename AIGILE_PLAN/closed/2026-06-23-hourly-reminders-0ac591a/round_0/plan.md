## Burst Plan

**Goal:** Deliver an hourly reminder system that creates a notification for a task's assignee every hour until the task is completed or unassigned, with a backend scheduler, a notifications read API, and a frontend notification surface.

**CHARTER alignment:** Advances "Complete backend API — all routers functional" (adds the missing notifications router) and "Frontend connected to live backend — no mock data" (adds a live notification surface). Honours Hard Spec "All schema changes via numbered migration files."

**Streams:** Three streams, sequenced then partially parallel. Stream A (backend foundation: migration + model + Notification schema + notifications router) is a hard prerequisite. Streams B (scheduler) and C (frontend) both depend on A and are pairwise file-disjoint, so B and C run in parallel after A merges.

### Stream A - Notifications foundation (schema, model, read API)

- Scope:
  - `database/004_task_reminders.sql` (NEW numbered migration — verify next free number by listing `database/`; current files are unnumbered `schema.sql`/`seed.sql`/`pgvector_setup.sql`, so confirm the project's numbering start with the Orchestrator; idempotent `ALTER TABLE tasks ADD COLUMN IF NOT EXISTS last_reminded_at TIMESTAMPTZ`, plus index `idx_tasks_reminder ON tasks (assigned_to, is_completed) WHERE assigned_to IS NOT NULL AND is_completed = FALSE`)
  - `database/schema.sql` (add the same `last_reminded_at` column to the canonical `tasks` table definition at lines 129-144 to keep bootstrap in sync, per the global "bootstrap.sql must stay in sync" rule)
  - `backend/app/models/models.py` (add `last_reminded_at: Mapped[Optional[datetime]]` to `Task`; the `Notification` model at lines 203-216 already has `user_id`, `type`, `title`, `body`, `entity_type`, `entity_id`, `is_read`, `created_at` — no change needed)
  - `backend/app/schemas/schemas.py` (NEW `NotificationOut` schema; verify it mirrors the existing `from_attributes` pattern used by `TaskOut`; add `last_reminded_at` to `TaskOut` only if the Orchestrator wants it surfaced — otherwise exclude)
  - `backend/app/api/v1/notifications.py` (NEW router, prefix `/notifications`, mirroring `tasks.py` structure: `GET /` list current user's notifications, `PATCH /{id}/read` mark read, `POST /{id}/read-all` or `PATCH /read-all` mark all read; all gated by `get_current_user` from `app.core.deps`)
  - `backend/app/main.py` (register the new router: add `notifications` to the `from app.api.v1 import ...` line 7 and add `app.include_router(notifications.router, prefix=PREFIX)` after the existing includes, lines 28-34)
- Excluded: scheduler code, `requirements.txt`, all frontend files
- Exports (interface contract):
  - `Notification` ORM unchanged; `Task.last_reminded_at` column available
  - REST: `GET /api/v1/notifications` -> `List[NotificationOut]` (fields: `id`, `user_id`, `type`, `title`, `body`, `entity_type`, `entity_id`, `is_read`, `created_at`), `PATCH /api/v1/notifications/{id}/read`, `PATCH /api/v1/notifications/read-all`
  - Reminder notification convention: `type="reminder"`, `entity_type="task"`, `entity_id=<task.id>` (note PG `entity_type` is an ENUM that already includes `'task'`)
- Dependency: none (foundation)
- Builder: claude

### Stream B - Hourly reminder scheduler

- Scope:
  - `backend/requirements.txt` (add `apscheduler==3.10.4` — AsyncIOScheduler integrates with FastAPI's event loop and needs no broker, unlike Celery; confirm version with the Orchestrator)
  - `backend/app/services/reminder_service.py` (NEW — the core job: open an `AsyncSessionLocal` from `app.db.session`, select tasks where `assigned_to IS NOT NULL AND is_completed = FALSE`, and for each eligible task insert a `Notification` and stamp `Task.last_reminded_at`; reuse the `select`/`async with` patterns already in `tasks.py` and `deps.py`)
  - `backend/app/core/scheduler.py` (NEW — construct the `AsyncIOScheduler`, register the hourly job, expose `start_scheduler()`/`shutdown_scheduler()`)
  - `backend/app/main.py` lifespan: a startup/shutdown hook to start and stop the scheduler. SHARED FILE with Stream A (see Shared files) — coordinate.
- Excluded: notifications router, schemas, models migration (consumes A's column), all frontend files
- Exports (interface contract):
  - `start_scheduler()` / `shutdown_scheduler()` callable from `main.py`
  - `run_task_reminders(session)` service function (testable in isolation)
- Case enumeration (scheduler job state machine — MANDATORY):
  - Happy path: task assigned, not completed, `last_reminded_at` older than ~1h (or null) -> create one reminder notification, update `last_reminded_at`
  - Empty/missing input: no eligible tasks -> job no-ops, no error
  - Malformed/orphaned: `assigned_to` points to a deleted/inactive user -> skip (the FK is `ON DELETE SET NULL`, so assigned_to becomes null and is filtered out; also guard against inactive users)
  - Partial/intermediate state: task just completed or unassigned between job runs -> excluded by the `is_completed=FALSE AND assigned_to IS NOT NULL` filter; no reminder
  - Missing dependency: scheduler not started (e.g. import/config failure) -> log and degrade gracefully, app still serves requests; DB unreachable mid-job -> catch, log, do not crash the scheduler thread; duplicate-run guard via `last_reminded_at` threshold so a restart within the hour does not double-send
- Dependency: Stream A (needs `Task.last_reminded_at` column and the agreed `Notification` reminder convention)
- Builder: claude

### Stream C - Frontend notification surface

- Scope:
  - `frontend/lib/api.ts` (NEW `notificationsApi` block: `list()`, `markRead(id)`, `markAllRead()`, mirroring the existing `tasksApi`/`projectsApi` axios pattern at lines 55-63)
  - `frontend/lib/types.ts` (NEW `Notification` TS interface matching `NotificationOut`)
  - `frontend/components/layout/NotificationBell.tsx` (NEW — bell with unread count, dropdown listing reminders, mark-read action; client component, polls `notificationsApi.list()` on an interval)
  - `frontend/components/layout/Header.tsx` (render `<NotificationBell />` in the actions area, lines 30-41) — verify with Orchestrator whether the bell belongs in Header or Sidebar; Header is the natural slot
- Excluded: all backend files, all other frontend pages
- Exports: visual notification bell + dropdown wired to the live `/notifications` API
- Dependency: Stream A (consumes `GET /api/v1/notifications` and `NotificationOut` shape)
- Builder: claude

**Shared files:**
- `backend/app/main.py` — written by BOTH Stream A (router registration) and Stream B (lifespan/scheduler hooks). This is a coordination point: the two edits touch different regions (router includes vs lifespan), but the file is a shared writer, so A and B are NOT pairwise disjoint on this file. Resolution: Stream A lands its `main.py` router change first (as the foundation merge); Stream B then layers its lifespan edit on top. Do not run A and B's `main.py` edits concurrently.
- `frontend/components/layout/Header.tsx` — written only by Stream C (not shared).

**Integration gate:**
- Stream A merges first. Verify: `uvicorn app.main:app` boots, `GET /api/v1/notifications` returns 200 with bearer token, migration `004_task_reminders.sql` applies idempotently against a fresh DB and re-runs cleanly (IF NOT EXISTS), `schema.sql` tasks table matches the migration.
- Streams B and C merge after A (parallel-safe except for B's `main.py` lifespan edit, which must rebase on A's merged `main.py`).
- Probe acceptance: assign a task to a user -> within the configured interval a `type="reminder"` notification row appears for that user and shows in the frontend bell; complete or unassign the task -> no further reminders; restart backend within the hour -> no duplicate reminder (last_reminded_at guard). Integration test covering the four scheduler cases above (eligible, completed, unassigned, inactive-user) must pass under pytest.

**Deferred to next Burst:**
- Real-time push (WebSocket/SSE) for instant bell updates — v0 uses frontend polling.
- Email/Slack delivery of reminders — v0 is in-app notifications only.
- Per-user reminder cadence configuration and quiet hours.
- Confirm the `database/` migration numbering convention with the Orchestrator (existing files are unnumbered); if a formal numbered series does not yet exist, this burst may need to establish `001_`..`003_` retroactively or document the scheme. AMBIGUITY flagged — resolve before Stream A build.

### Critical Files for Implementation
- backend/app/main.py
- backend/app/models/models.py
- database/schema.sql
- backend/app/api/v1/tasks.py
- frontend/lib/api.ts
