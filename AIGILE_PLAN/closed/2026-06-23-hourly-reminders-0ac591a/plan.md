## Burst Plan

**Goal:** Deliver an hourly reminder system that creates a notification for a task's assignee every hour until the task is completed or unassigned, with a Railway Cron Service, a notifications read API, and a frontend notification surface.

**CHARTER alignment:** Advances "Complete backend API — all routers functional" (adds the missing notifications router) and "Frontend connected to live backend — no mock data" (adds a live notification surface). Honours Hard Spec "All schema changes via numbered migration files."

**Streams:** Three streams, sequenced then partially parallel. Stream A (backend foundation: migration + model + Notification schema + notifications router) is a hard prerequisite. Streams B (scheduler) and C (frontend) both depend on A and are pairwise file-disjoint, so B and C run in parallel after A merges.

### Stream A - Notifications foundation (schema, model, read API)

- Scope:
  - `database/001_task_reminders.sql` (NEW numbered migration — starts the numbered series at `001_`; existing files (`schema.sql`/`seed.sql`/`pgvector_setup.sql`) stay unnumbered and are NOT renamed since they are already applied; idempotent `ALTER TABLE tasks ADD COLUMN IF NOT EXISTS last_reminded_at TIMESTAMPTZ`, plus index `idx_tasks_reminder ON tasks (assigned_to, is_completed) WHERE assigned_to IS NOT NULL AND is_completed = FALSE`)
  - `database/schema.sql` (add the same `last_reminded_at` column to the canonical `tasks` table definition at lines 129-144 to keep bootstrap in sync, per the global "bootstrap.sql must stay in sync" rule)
  - `backend/app/models/models.py` (add `last_reminded_at: Mapped[Optional[datetime]]` to `Task`; add a Python `EntityType` Enum class and change `Notification.entity_type` from `String(50)` to `SQLAlchemyEnum(EntityType, name="entity_type", ...)` — the explicit `name="entity_type"` parameter matches the existing PostgreSQL enum name exactly (schema.sql:19, schema.sql:219) so the ORM mapping matches the PostgreSQL `entity_type` enum column defined in `schema.sql`; the rest of the `Notification` model at lines 203-216 already has `user_id`, `type`, `title`, `body`, `entity_type`, `entity_id`, `is_read`, `created_at` — no further change needed)
  - `backend/app/schemas/schemas.py` (NEW `NotificationOut` schema; verify it mirrors the existing `from_attributes` pattern used by `TaskOut`; add `last_reminded_at` to `TaskOut` only if the Orchestrator wants it surfaced — otherwise exclude)
  - `backend/app/api/v1/notifications.py` (NEW router, prefix `/notifications`, mirroring `tasks.py` structure: `GET /` list current user's notifications (defaults to last 20, unread-first ordering, newest-first; supports `?limit=N` and `?unread=true` query parameters), `PATCH /{id}/read` mark read, `POST /{id}/read-all` or `PATCH /read-all` mark all read; all gated by `get_current_user` from `app.core.deps`, and all single-notification mutations constrain by both notification id AND `user_id = current_user.id`)
  - `backend/app/main.py` (register ONLY the notifications router: add `notifications` to the `from app.api.v1 import ...` line 7 and add `app.include_router(notifications.router, prefix=PREFIX)` after the existing includes, lines 28-34. Stream A does NOT add the internal router — Stream B adds that line as its own sequential edit after A merges)
- Excluded: scheduler code, the internal router include in `main.py`, `requirements.txt`, all frontend files
- Exports (interface contract):
  - `Notification` ORM with `entity_type` mapped via `SQLAlchemyEnum(EntityType, name="entity_type")`; `Task.last_reminded_at` column available
  - REST: `GET /api/v1/notifications` -> `List[NotificationOut]` (fields: `id`, `user_id`, `type`, `title`, `body`, `entity_type`, `entity_id`, `is_read`, `created_at`; defaults to last 20 unread-first/newest-first, accepts `?limit=N&unread=true`), `PATCH /api/v1/notifications/{id}/read` (ownership-scoped by `user_id = current_user.id`), `PATCH /api/v1/notifications/read-all`
  - Reminder notification convention: `type="reminder"`, `entity_type="task"`, `entity_id=<task.id>` (note PG `entity_type` is an ENUM that already includes `'task'`)
- Dependency: none (foundation)
- Builder: claude

### Stream B - Hourly reminder scheduler

- Scope:
  - `backend/requirements.txt` (REMOVE APScheduler from scope; add `pytest`, `pytest-asyncio`, `httpx` for the integration tests)
  - `backend/app/services/reminder_service.py` (NEW — the core job: open an `AsyncSessionLocal` from `app.db.session`, select tasks where `assigned_to IS NOT NULL AND is_completed = FALSE AND (last_reminded_at IS NULL OR last_reminded_at < now() - interval '1 hour')` joined to `users` with `AND users.is_active = TRUE`, and for each eligible task insert a `Notification` and stamp `Task.last_reminded_at`; reuse the `select`/`async with` patterns already in `tasks.py` and `deps.py`. The one-hour threshold and the `users.is_active = TRUE` join condition are part of the core query contract, not just the case enumeration)
  - `backend/app/api/v1/internal.py` (NEW — `POST /api/v1/internal/run-reminders` endpoint gated by a `CRON_SECRET` env var; calls `run_task_reminders(session)`. Replaces the in-process APScheduler approach: Railway Cron Service triggers this endpoint hourly)
  - `backend/app/main.py` (Stream B's sequential edit AFTER Stream A merges: add `internal` to the `from app.api.v1 import ...` line and add `app.include_router(internal.router, prefix=PREFIX)` after Stream A's notifications include. This edit must rebase on Stream A's merged `main.py` — main.py is a sequenced shared file: A first (notifications router), then B (internal router))
  - `backend/tests/test_reminders.py` (NEW — integration tests covering the four scheduler cases: eligible, completed, unassigned, inactive-user; uses `pytest`/`pytest-asyncio`/`httpx`. The inactive-user case must verify the `users.is_active = TRUE` filter in the query itself — i.e. an eligible task assigned to an inactive user produces NO reminder because the query excludes it, not merely that the case is listed)
  - `railway.json` (NEW — documents the Railway Cron Service setup that triggers `POST /api/v1/internal/run-reminders` hourly with the `CRON_SECRET`)
- Excluded: notifications router, schemas, models migration (consumes A's column), all frontend files
- Exports (interface contract):
  - `run_task_reminders(session)` service function (testable in isolation)
  - `POST /api/v1/internal/run-reminders` internal endpoint (gated by `CRON_SECRET`), triggered by Railway Cron
- Case enumeration (scheduler job state machine — MANDATORY):
  - Happy path: task assigned, not completed, `last_reminded_at` older than ~1h (or null) -> create one reminder notification, update `last_reminded_at`
  - Empty/missing input: no eligible tasks -> job no-ops, no error
  - Malformed/orphaned: `assigned_to` points to a deleted/inactive user -> skip. The FK is `ON DELETE SET NULL`, so a deleted user's `assigned_to` becomes null and is filtered out; an inactive (not deleted) user is excluded by the `users.is_active = TRUE` join condition in the core query
  - Partial/intermediate state: task just completed or unassigned between job runs -> excluded by the `is_completed=FALSE AND assigned_to IS NOT NULL` filter; no reminder
  - Missing dependency: DB unreachable mid-job -> catch, log, do not crash; duplicate-run guard via `last_reminded_at` threshold in the core query so a re-trigger within the hour does not double-send. Multi-worker overlap is avoided by construction: Railway Cron triggers a single endpoint invocation rather than running an in-process scheduler in every worker.
- Dependency: Stream A (needs `Task.last_reminded_at` column and the agreed `Notification` reminder convention)
- Builder: claude

### Stream C - Frontend notification surface

- Scope:
  - `frontend/lib/api.ts` (NEW `notificationsApi` block: `list()`, `markRead(id)`, `markAllRead()`, mirroring the existing `tasksApi`/`projectsApi` axios pattern at lines 55-63)
  - `frontend/lib/types.ts` (NEW `Notification` TS interface matching `NotificationOut`)
  - `frontend/components/layout/NotificationBell.tsx` (NEW — bell with unread count, dropdown listing reminders, mark-read action; client component, polls `notificationsApi.list()` every 30 seconds via a `setInterval` cleared on unmount, so the bell updates without a page reload)
  - `frontend/app/(dashboard)/layout.tsx` (mount `<NotificationBell />` unconditionally so the bell is global across all dashboard pages, rather than in the conditional Header actions area)
- Excluded: all backend files, all other frontend pages
- Exports: visual notification bell + dropdown wired to the live `/notifications` API, refreshing on a 30-second poll
- Dependency: Stream A (consumes `GET /api/v1/notifications` and `NotificationOut` shape)
- Builder: claude

**Shared files:**
- `backend/app/main.py` — sequenced shared writer: Stream A first edits it to register the notifications router, then Stream B edits it to register the internal router after A merges. Stream B's main.py edit must rebase on Stream A's merged main.py. The two router-include edits are coordinated by sequencing (A then B), not by a single owner.
- `frontend/app/(dashboard)/layout.tsx` — written only by Stream C (not shared).

**Integration gate:**
- Stream A merges first. Verify: `uvicorn app.main:app` boots with only the notifications router registered, `GET /api/v1/notifications` returns 200 with bearer token, migration `001_task_reminders.sql` applies idempotently against a fresh DB and re-runs cleanly (IF NOT EXISTS) without a DuplicateObject error on the `entity_type` enum, `schema.sql` tasks table matches the migration. Verify `GET /notifications?limit=N&unread=true` returns the bounded, unread-first, newest-first list. Verify a cross-user `PATCH /notifications/{id}/read` against another user's notification returns 403 (ownership guard).
- Streams B and C merge after A. B's internal-router include line rebases on A's merged `main.py`; verify `uvicorn app.main:app` still boots with both routers registered. Verify `railway.json` is present and `POST /api/v1/internal/run-reminders` responds (gated by `CRON_SECRET`) — railway.json presence plus the endpoint responding is the Railway Cron probe artefact.
- Probe acceptance: assign a task to a user -> within the configured interval a `type="reminder"` notification row appears for that user and shows in the frontend bell, with the bell updating within ~30 seconds of the reminder being created without a page reload (30-second poll); complete or unassign the task -> no further reminders; re-trigger the internal endpoint within the hour -> no duplicate reminder (last_reminded_at guard). Integration test covering the four scheduler cases above (eligible, completed, unassigned, inactive-user) must pass under pytest (`pytest`/`pytest-asyncio`/`httpx`), with the inactive-user case confirming the `users.is_active = TRUE` query filter suppresses the reminder.

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
