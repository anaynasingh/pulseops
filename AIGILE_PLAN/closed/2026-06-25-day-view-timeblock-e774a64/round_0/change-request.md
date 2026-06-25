# Change Request: Round 0 → Round 1

## Modifications
- API contract: `GET /tasks/day?start=<iso>&end=<iso>` (was `?date=&tz_offset=`). Half-open `[start,end)` filter on `scheduled_at`, tz-aware UTC. Response still `{date, scheduled, unscheduled}` (date echoed as label).
- `GET /tasks/day` query gains `.options(selectinload(Task.assignee), selectinload(Task.project))`.
- `duration_minutes` in TaskCreate/TaskUpdate becomes `Field(default=None, ge=15, le=1440)`.
- Frontend `tasksApi.day(startIso, endIso, dateStr)` (was `day(date, tzOffset)`).
- react-query key `["tasks","day",dateStr]`.
- Frontend types: `scheduled_at: string | null`, `duration_minutes: number | null` (not optional `?`).
- day/page.tsx: add "Outside working hours" strip for tasks scheduled before DAY_START_HOUR or at/after DAY_END_HOUR; click-to-assign dropdown only offers in-grid hours; clamp overflow blocks.

## Additions
- None beyond the above (no new files; all changes land in the already-scoped files).

## Deletions
- Remove `tz_offset` query param and offset arithmetic from the design.

## Cascading consequences
- No scope-file changes: every modification lands in files already in Stream A or Stream B scope.
- Stream A files unchanged in set: models.py, schemas.py, tasks.py, main.py, database/004_task_scheduling.sql.
- Stream B files unchanged in set: types.ts, api.ts, Sidebar.tsx, day/page.tsx.
- Interface contract changed (start/end ISO instead of date/tz_offset) — both streams reference the new contract; still lockable upfront, still parallel-safe.
