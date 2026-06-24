# Preservation check: round_0 → round_1

## Verdict: PASSED — all diff hunks authorised

### Hunk analysis

1. **Stream A migration filename** `004_` → `001_task_reminders.sql` — AUTHORISED (change-request §Additions: "database/001_task_reminders.sql added to Stream A scope")
2. **Stream A models.py** — adds EntityType enum + SQLAlchemyEnum mapping — AUTHORISED (change-request §Additions: "models.py scope expanded with EntityType enum + SQLAlchemyEnum")
3. **Stream A notifications.py** — adds limit/unread params + ownership constraint — AUTHORISED (change-request §Modifications: H2 and H7 gate updates)
4. **Stream A Exports** — updated ORM description + REST contract — AUTHORISED (follows from #2 and #3)
5. **Stream B requirements.txt** — removes apscheduler, adds pytest/pytest-asyncio/httpx — AUTHORISED (change-request §Modifications: "requirements.txt swapped from apscheduler to pytest...")
6. **Stream B scope** — removes scheduler.py, adds internal.py + test_reminders.py + railway.json — AUTHORISED (change-request §Modifications: "Stream B scope: REMOVE scheduler.py and APScheduler, REPLACE with internal endpoint pattern")
7. **Stream B Exports** — removes start/shutdown_scheduler, adds internal endpoint — AUTHORISED (follows from #6)
8. **Stream B case enumeration missing-dependency** — updates to reflect Railway Cron model — AUTHORISED (follows from #6)
9. **Stream C layout.tsx** — replaces Header.tsx with layout.tsx — AUTHORISED (change-request §Modifications: "Move NotificationBell mount from Header.tsx to layout.tsx")
10. **Shared files section** — updated to reflect single-writer main.py, layout.tsx — AUTHORISED (change-request §Modifications: shared files section updated)
11. **Integration gate** — adds limit/unread test, 403 ownership test, removes `main.py` rebase coordination — AUTHORISED (change-request §Modifications: integration gate updated)
12. **Deferred section** — removed migration numbering ambiguity clause — AUTHORISED (change-request §Deletions: resolved ambiguity removed)

### Unauthorised hunks: NONE
