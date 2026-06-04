# Round 0 Determination

## H1 — ORM/schema entity_type mismatch
**Disposition:** ABSORB-PLAN
**Reason:** Fix the ORM. Add a Python `EntityType` Enum class and map `Notification.entity_type` as `SQLAlchemyEnum`. Keeps DB schema strict and type-safe. Stream A scope must include this ORM change.

## H2 — Notification ownership not gated
**Disposition:** ABSORB-GATE
**Reason:** Add `AND user_id = current_user.id` filter to all `PATCH /notifications/{id}/read` queries. Integration gate must include a cross-user 403 test.

## H3 — Duplicate reminders on multi-worker / APScheduler risk
**Disposition:** ABSORB-PLAN
**Reason:** Orchestrator confirmed Railway deployment. APScheduler in-process breaks on multi-worker scale. Replace Stream B with Railway Cron Service + internal endpoint `POST /api/v1/internal/run-reminders` gated by `CRON_SECRET` env var. Remove `scheduler.py` and APScheduler dependency. `reminder_service.py` remains (called by the endpoint). `main.py` needs no lifespan hook for scheduler.

## H4 — Migration numbering internally inconsistent
**Disposition:** ABSORB-PLAN
**Reason:** Start numbered series at `001_task_reminders.sql`. Do NOT rename existing unnumbered files (schema.sql, seed.sql, pgvector_setup.sql). Simpler; existing files are already applied.

## H5 — pytest not in scope/requirements
**Disposition:** ABSORB-GATE
**Reason:** Declare test files in Stream B scope: `backend/tests/test_reminders.py`. Add `pytest`, `pytest-asyncio`, `httpx` to `backend/requirements.txt`. Integration gate must show these tests passing.

## H6 — Bell hidden on pages without `actions` prop
**Disposition:** ABSORB-PLAN
**Reason:** Move `<NotificationBell />` mount to `frontend/app/(dashboard)/layout.tsx` instead of the conditional Header actions area. Stream C scope updated accordingly.

## H7 — Unbounded notification list
**Disposition:** ABSORB-GATE
**Reason:** `GET /notifications` must default to last 20 unread-first, support `?limit=N` and `?unread=true`. Stream A integration gate updated.

## Rejected alternatives
- APScheduler with single-worker lock: rejected — fragile on Railway, introduces app-level concurrency guards that duplicate what Railway Cron gives for free.
- Fix DB column to VARCHAR instead of ORM to SQLAlchemyEnum: rejected — Orchestrator chose ORM fix; keeps DB-level enum validation.
- Retroactively rename existing migration files: rejected — Orchestrator chose start-fresh-at-001 to avoid touching existing applied files.
