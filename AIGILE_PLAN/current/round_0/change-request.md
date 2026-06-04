# Change Request: Round 0 → Round 1

## Additions

- `database/001_task_reminders.sql` added to Stream A scope (replaces the `004_` filename; existing files stay unnumbered)
- `backend/app/api/v1/internal.py` (or `backend/app/api/v1/notifications.py` internal route) added to Stream B scope — new `POST /api/v1/internal/run-reminders` endpoint gated by `CRON_SECRET`
- `backend/tests/test_reminders.py` added to Stream B scope
- `railway.json` or Railway Cron config note added to Stream B scope (documents the cron service setup)
- `backend/app/models/models.py` scope expanded: add `EntityType` Python Enum class + change `Notification.entity_type` mapping to `SQLAlchemyEnum`
- `GET /notifications` query parameters `?limit=N&unread=true` and `newest-first` ordering added to Stream A integration gate

## Modifications

- Stream B scope: REMOVE `backend/app/core/scheduler.py` and APScheduler from `backend/requirements.txt`. REPLACE with Railway Cron + internal endpoint pattern. `backend/app/services/reminder_service.py` remains but is called by the new endpoint, not by a scheduler.
- Stream B `main.py` entry: REMOVE lifespan/startup hook for scheduler. `main.py` is now touched only by Stream A (router registration). Shared file conflict resolved — `main.py` is no longer a coordination point between A and B.
- Stream C scope: MOVE `<NotificationBell />` mount from `frontend/components/layout/Header.tsx` (conditional actions area) to `frontend/app/(dashboard)/layout.tsx` (unconditional). Header.tsx no longer in Stream C scope.
- Integration gate Stream A: add ownership guard test (cross-user 403) and `?limit`/`?unread` acceptance.
- Integration gate Stream B: add pytest run for eligible/completed/unassigned/inactive-user cases.

## Deletions

- `backend/app/core/scheduler.py` removed from plan (was in Stream B, now not built)
- `frontend/components/layout/Header.tsx` removed from Stream C scope (bell moves to layout)
- APScheduler removed from `backend/requirements.txt` scope

## Cascading consequences

Files dropped from Scope:
- `backend/app/core/scheduler.py` — removed entirely. No Integration gate, test, or trap-list references it; the file is new (not yet created), so no orphans.
- `frontend/components/layout/Header.tsx` — removed from Stream C. No Integration gate items reference it directly; `<NotificationBell />` mount reference updated to `layout.tsx` in Modifications above.
- APScheduler from `backend/requirements.txt` — still in scope but content changes (apscheduler line removed, pytest/pytest-asyncio/httpx added).

References to dropped items elsewhere in the plan: none orphaned. All integration gate items updated in §Modifications. No Bats tests, trap-list paragraphs, or Excluded-section justifications reference the dropped files.
